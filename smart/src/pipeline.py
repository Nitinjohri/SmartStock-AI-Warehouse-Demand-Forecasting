import os
import sys
import pandas as pd
import numpy as np

from Generate_data import generate_all
from Feature_engineering import build_features
from Prophet_model import ProphetForecaster
from XGBoost_model import XGBoostForecaster
from Evaluator import walk_forward_evaluate, ensemble_predictions, select_best_model
from Reorder import calculate_reorder_for_sku, generate_purchase_orders


# ── Configuration ────────────────────────────────────────────────────────────
DATA_PATH       = r"C:\Users\NITIN JOHRI\OneDrive\Desktop\Retail_Dataset2.csv"
MODEL_DIR       = os.path.join(os.path.dirname(__file__), "..", "models")
OUTPUT_DIR      = os.path.join(os.path.dirname(__file__), "..", "output")
# --- Training Configuration ---
TRAIN_ALL_SKUS  = False  # Set to True to train ALL products, False for Top 100
MAX_SKUS_LIMIT  = 100    # Used if TRAIN_ALL_SKUS is False
HORIZON_DAYS    = 30
SERVICE_LEVEL_Z = 1.65   # 95 % service level
DEFAULT_LEAD_TIME = 7    # default lead time if not in dataset
DEFAULT_STOCK     = 500  # simulated current stock per SKU

# ── Column mapping: YOUR dataset → pipeline expected format ──────────────────
COLUMN_MAP = {
    "Product_Code":     "sku_id",
    "Product_Category": "sku_name",
    "Date":             "date",
    "Order_Demand":     "quantity_sold",
    "Promo":            "is_promotion",
}


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns from Retail_Dataset2.csv to the format the pipeline expects."""
    df = df.rename(columns=COLUMN_MAP)

    # Parse date (handles mixed formats like m/d/yyyy)
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    # Ensure quantity_sold is numeric (remove commas if any, cast to int)
    df["quantity_sold"] = pd.to_numeric(
        df["quantity_sold"].astype(str).str.replace(",", ""), errors="coerce"
    ).fillna(0).astype(int)

    # Add lead_time_days if missing
    if "lead_time_days" not in df.columns:
        df["lead_time_days"] = DEFAULT_LEAD_TIME

    # Ensure is_promotion is 0/1
    df["is_promotion"] = df["is_promotion"].astype(int)

    return df


def run_pipeline():
    """Execute the full SmartStock pipeline."""

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Step 1: Load & map data ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1 — Data Loading & Column Mapping")
    print("=" * 60)

    if os.path.exists(DATA_PATH):
        print(f"  Loading data from {DATA_PATH}")
        raw_df = pd.read_csv(DATA_PATH)
        print(f"  Original columns: {list(raw_df.columns)}")
        raw_df = map_columns(raw_df)
        print(f"  Mapped columns:   {list(raw_df.columns)}")
    else:
        print("  Dataset not found! Generating synthetic data …")
        raw_df = generate_all(output_path=DATA_PATH)

    print(f"  Rows: {len(raw_df):,}  |  SKUs: {raw_df['sku_id'].nunique()}")

    # Build SKU list from the actual data
    sku_list = raw_df.groupby("sku_id").agg(
        sku_name=("sku_name", "first"),
        lead_time_days=("lead_time_days", "first"),
    ).reset_index().to_dict("records")

    # --- SKU Selection Logic ---
    print("\nTRAINING MODE SELECTION:")
    user_choice = input(" [1] Train ALL SKUs (Very long)\n [2] Train top 100 (Recommended)\n Choice [1 or 2]: ").strip()
    
    if user_choice == "1":
        print(f"  Training on all {len(sku_list)} SKUs natively without artificial hardcoded limits")
    else:
        limit = MAX_SKUS_LIMIT
        top_skus = raw_df.groupby("sku_id")["quantity_sold"].sum().nlargest(limit).index
        sku_list = [s for s in sku_list if s["sku_id"] in top_skus]
        print(f"  Training on top {len(sku_list)} SKUs by sales volume (Limit: {MAX_SKUS_LIMIT})")

    # ── Step 2: Feature engineering ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2 — Feature Engineering")
    print("=" * 60)

    featured_df = build_features(raw_df, drop_na=False)
    print(f"  Features added: {featured_df.shape[1] - raw_df.shape[1]} new columns")

    # ── Step 3: Train & evaluate per SKU ─────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3 — Model Training & Evaluation")
    print("=" * 60)

    all_forecasts   = []
    reorder_results = []
    summary_rows    = []

    for i, sku in enumerate(sku_list, 1):
        sku_id    = sku["sku_id"]
        sku_name  = sku["sku_name"]
        lead_time = sku["lead_time_days"]
        # Calculate a cohesive baseline stock derived natively from historical sales data (e.g. 3-weeks of inventory)
        total_sales = raw_df[raw_df["sku_id"] == sku_id]["quantity_sold"].sum()
        days_in_data = raw_df["date"].nunique() if "date" in raw_df.columns else 365
        avg_daily = total_sales / days_in_data if days_in_data > 0 else 0
        current_stock = max(int(avg_daily * 21), 50)

        print(f"\n  ── [{i}/{len(sku_list)}] {sku_id}: {sku_name} ──")

        # --- Train Prophet ---
        prophet = ProphetForecaster(sku_id=sku_id, horizon_days=HORIZON_DAYS)
        prophet.train(featured_df)

        # --- Train XGBoost ---
        xgb_model = XGBoostForecaster(sku_id=sku_id, horizon_days=HORIZON_DAYS)
        xgb_model.train(featured_df)
        xgb_preds = xgb_model.predict(featured_df)

        # --- Handle Prophet possibly skipping (too few rows) ---
        if prophet.model is not None:
            prophet_preds = prophet.predict(featured_df)

            # --- Cross-validation ---
            print("  Running walk-forward CV …")
            prophet_metrics = walk_forward_evaluate(prophet, featured_df)
            xgb_metrics     = walk_forward_evaluate(xgb_model, featured_df)

            # --- Ensemble ---
            ens_preds   = ensemble_predictions(prophet_preds, xgb_preds, prophet_weight=0.5)
            best_model  = select_best_model(prophet_metrics, xgb_metrics)

            # Pick forecasts from the best model
            if best_model == "prophet":
                chosen_preds = prophet_preds
            elif best_model == "xgboost":
                chosen_preds = xgb_preds
            else:
                chosen_preds = ens_preds
        else:
            print(f"  [Fallback] Using XGBoost-only for {sku_id} (Prophet had insufficient data)")
            xgb_metrics = walk_forward_evaluate(xgb_model, featured_df)
            prophet_metrics = {"mape": float("inf"), "rmse": float("inf"), "mae": float("inf")}
            best_model = "xgboost"
            chosen_preds = xgb_preds

        all_forecasts.append(chosen_preds)

        # --- Reorder calculation ---
        reorder = calculate_reorder_for_sku(
            sku_id=sku_id,
            sku_name=sku_name,
            historical_df=raw_df,
            forecast_df=chosen_preds,
            current_stock=current_stock,
            lead_time_days=lead_time,
            service_level_z=SERVICE_LEVEL_Z,
        )
        reorder_results.append(reorder)

        summary_rows.append({
            "sku_id":           sku_id,
            "sku_name":         sku_name,
            "best_model":       best_model,
            "prophet_mape":     prophet_metrics["mape"],
            "xgb_mape":         xgb_metrics["mape"],
            "forecast_30d":     reorder.forecast_30d,
            "current_stock":    current_stock,
            "safety_stock":     reorder.safety_stock,
            "reorder_point":    reorder.reorder_point,
            "days_to_stockout": reorder.days_until_stockout,
            "stockout_risk":    reorder.stockout_risk,
        })

        # --- Save models ---
        prophet.save(os.path.join(MODEL_DIR, f"prophet_{sku_id}.pkl"))
        xgb_model.save(os.path.join(MODEL_DIR, f"xgboost_{sku_id}.pkl"))

    # ── Step 4: Generate purchase orders ─────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4 — Purchase Order Generation")
    print("=" * 60)

    po_df = generate_purchase_orders(reorder_results)

    if po_df.empty:
        print("  ✅ All SKUs are well-stocked. No purchase orders needed.")
    else:
        print(f"  ⚠️  {len(po_df)} purchase order(s) generated:\n")
        print(po_df.to_string(index=False))

    # ── Step 5: Save outputs ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 5 — Saving Outputs")
    print("=" * 60)

    # Forecasts
    forecast_df = pd.concat(all_forecasts, ignore_index=True)
    forecast_path = os.path.join(OUTPUT_DIR, "forecasts.csv")
    forecast_df.to_csv(forecast_path, index=False)
    print(f"  Forecasts   → {forecast_path}")

    # Summary
    summary_df = pd.DataFrame(summary_rows)
    summary_path = os.path.join(OUTPUT_DIR, "pipeline_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"  Summary     → {summary_path}")

    # Purchase orders
    if not po_df.empty:
        po_path = os.path.join(OUTPUT_DIR, "purchase_orders.csv")
        po_df.to_csv(po_path, index=False)
        print(f"  POs         → {po_path}")

    print("\n" + "=" * 60)
    print("✅  Pipeline complete!")
    print("=" * 60)

    return summary_df, forecast_df, po_df


if __name__ == "__main__":
    run_pipeline()