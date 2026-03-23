"""
services/pipeline_service.py
Singleton service that loads trained models and serves predictions.
This is the bridge between FastAPI and the ML pipeline.
"""

import os
import pickle
import threading
import pandas as pd

# Fallback to CWD to avoid Uvicorn __file__ encoding corruption on Windows with em-dash paths
cwd = os.getcwd()
if os.path.basename(cwd) == "backend" or os.path.basename(cwd) == "app":
    project_root = os.path.abspath(os.path.join(cwd, ".."))
else:
    project_root = cwd

# Environment-aware paths for Docker transition
ML_PIPELINE_PATH = os.environ.get("ML_PIPELINE_PATH", os.path.join(project_root, "smart"))
MODELS_DIR       = os.path.join(ML_PIPELINE_PATH, "models")
OUTPUTS_DIR      = os.path.join(ML_PIPELINE_PATH, "output")
DATA_PATH        = os.environ.get("DATA_PATH", r"C:\Users\NITIN JOHRI\OneDrive\Desktop\Retail_Dataset2.csv")
METRICS_PATH     = os.path.join(OUTPUTS_DIR, "pipeline_summary.csv")

# Default current stock levels (replace with DB in production)
DEFAULT_STOCK = {
    "SKU-001": 120,
    "SKU-002": 80,
    "SKU-003": 45,
    "SKU-004": 15,
    "SKU-005": 200,
}


class PipelineService:
    """
    Loads trained Prophet + XGBoost models from disk.
    Serves forecasts, inventory status, and purchase orders.
    """

    def __init__(self):
        self._prophet_models  = {}
        self._xgb_models      = {}
        self._sales_df        = None
        self._metrics         = {}
        self._sku_meta        = {}      # ALL SKUs from the dataset
        self._trained_skus    = set()   # Only SKUs with at least one trained model
        self._last_run        = None
        self._loaded          = False
        self._is_training     = False
        self._lock            = threading.Lock()
        self._forecasts_df    = None
        self._inventory_cache = None   # Cache computed inventory to avoid recomputation

    def load(self):
        """Load all trained models and data into memory safely using a lock."""
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return
                
            print("[Service] Loading models and data...")

            import sys
        
            # Get absolute path to the project root safely using cwd
            cwd = os.getcwd()
            if os.path.basename(cwd) == "backend" or os.path.basename(cwd) == "app":
                p_root = os.path.abspath(os.path.join(cwd, ".."))
            else:
                p_root = cwd

            # Add smart/src to sys.path so we can import 'pipeline', 'Reorder', etc.
            SMART_SRC_PATH = os.environ.get("SMART_SRC_PATH", os.path.join(p_root, "smart", "src"))
            if SMART_SRC_PATH not in sys.path:
                sys.path.insert(0, SMART_SRC_PATH)

            # Load sales data
            if os.path.exists(DATA_PATH):
                from pipeline import map_columns
                from Feature_engineering import build_features
                raw_df = pd.read_csv(DATA_PATH)
                self._sales_df = map_columns(raw_df)
                self._sales_df = build_features(self._sales_df, drop_na=False)
                
                # Build SKU metadata
                for _, row in self._sales_df.drop_duplicates("sku_id").iterrows():
                    self._sku_meta[row["sku_id"]] = {
                        "sku_name":      row["sku_name"],
                        "lead_time_days": row["lead_time_days"],
                    }
                print(f"[Service] Loaded sales data: {len(self._sales_df):,} rows, {len(self._sku_meta)} SKUs")

            # Load metrics
            if os.path.exists(METRICS_PATH):
                metrics_df = pd.read_csv(METRICS_PATH)
                for _, row in metrics_df.iterrows():
                    # Based on the pipeline_summary.csv columns
                    sku = row["sku_id"]
                    best_model = row.get("best_model", "xgboost")
                    
                    # Convert explicitly to python float, replacing NaN with None
                    prophet_mape = float(row["prophet_mape"]) if pd.notna(row.get("prophet_mape")) else None
                    xgb_mape = float(row["xgb_mape"]) if pd.notna(row.get("xgb_mape")) else None
                    
                    best_mape = prophet_mape if best_model == "prophet" else xgb_mape

                    self._metrics[sku] = {
                        "best_model": str(best_model),
                        "prophet_mape": prophet_mape,
                        "xgb_mape": xgb_mape,
                        "best_mape": best_mape
                    }

            # Load ALL Prophet and XGBoost models from the models directory
            if os.path.exists(MODELS_DIR):
                model_files = os.listdir(MODELS_DIR)
                for fname in model_files:
                    path = os.path.join(MODELS_DIR, fname)
                    if fname.endswith(".pkl") and fname.startswith("prophet_"):
                        sku_id = fname.replace("prophet_", "").replace(".pkl", "")
                        try:
                            with open(path, "rb") as f:
                                loaded = pickle.load(f)
                                # Only keep models that were actually trained
                                if hasattr(loaded, 'model') and loaded.model is not None:
                                    self._prophet_models[sku_id] = loaded
                        except Exception as e:
                            print(f"[Service] Failed to load Prophet model for {sku_id}: {e}")
                    elif fname.endswith(".pkl") and fname.startswith("xgboost_"):
                        sku_id = fname.replace("xgboost_", "").replace(".pkl", "")
                        try:
                            with open(path, "rb") as f:
                                self._xgb_models[sku_id] = pickle.load(f)
                        except Exception as e:
                            print(f"[Service] Failed to load XGBoost model for {sku_id}: {e}")

            print(f"[Service] Loaded {len(self._prophet_models)} Prophet + {len(self._xgb_models)} XGBoost models")

            # Build the dynamic set of trained SKUs (adapts to top-10, top-100, or all)
            self._trained_skus = set(self._prophet_models.keys()) | set(self._xgb_models.keys())
            print(f"[Service] {len(self._trained_skus)} SKUs have at least one trained model")
            
            # Load precomputed forecasts if available to speed up get_forecast
            forecasts_path = os.path.join(OUTPUTS_DIR, "forecasts.csv")
            if os.path.exists(forecasts_path):
                self._forecasts_df = pd.read_csv(forecasts_path)
                print("[Service] Loaded precomputed forecasts for fast serving")

            # Precompute Inventory Cache from summary (Instant Dashboard Loading)
            if os.path.exists(METRICS_PATH):
                try:
                    metrics_df = pd.read_csv(METRICS_PATH)
                    items = []
                    for _, row in metrics_df.iterrows():
                        sku_id = row["sku_id"]
                        
                        # Calculate avg_daily_demand on the fly from sales data
                        avg_daily = 0.0
                        if self._sales_df is not None:
                            hist_sku = self._sales_df[self._sales_df["sku_id"] == sku_id]
                            total_sales = hist_sku["quantity_sold"].sum() if not hist_sku.empty else 0
                            days_in_data = hist_sku["date"].nunique() if not hist_sku.empty else 365
                            avg_daily = float(total_sales / days_in_data) if days_in_data > 0 else 0.0

                        items.append({
                            "sku_id":              str(sku_id),
                            "sku_name":            str(row["sku_name"]),
                            "current_stock":       int(row["current_stock"]),
                            "avg_daily_demand":    round(avg_daily, 1),
                            "reorder_point":       int(row["reorder_point"]),
                            "safety_stock":        int(row["safety_stock"]),
                            "days_until_stockout": int(row["days_to_stockout"]) if pd.notna(row["days_to_stockout"]) else None,
                            "stockout_risk":       str(row["stockout_risk"]),
                            "forecast_30d":        int(row["forecast_30d"]),
                            # Fields needed for purchase orders but not in summary
                            "lead_time_days":      self._sku_meta.get(sku_id, {}).get("lead_time_days", 7),
                            "suggested_order_qty": int(max(int(row["forecast_30d"]), int(row["safety_stock"]) * 2)), 
                        })
                    
                    self._inventory_cache = {
                        "total_skus":     len(items),
                        "critical_count": sum(1 for i in items if i["stockout_risk"] == "critical"),
                        "high_count":     sum(1 for i in items if i["stockout_risk"] == "high"),
                        "items":          sorted(items, key=lambda x: x.get("days_until_stockout") or 999),
                    }
                    print(f"[Service] Precomputed inventory cache for {len(items)} SKUs from summary")
                except Exception as e:
                    print(f"[Service] Failed to precompute inventory cache: {e}")

            self._loaded = True

    # ── Forecast ──────────────────────────────────────────────────────────────

    def _run_models_for_forecast(self, sku_id: str, horizon: int) -> pd.DataFrame:
        prophet_preds, xgb_preds = None, None

        # Prophet forecast
        if sku_id in self._prophet_models:
            try:
                prophet_preds = self._prophet_models[sku_id].predict(self._sales_df)
                prophet_preds["model"] = "prophet"
            except Exception as e:
                print(f"[Service] Prophet predict failed for {sku_id}: {e}")

        # XGBoost forecast
        if sku_id in self._xgb_models:
            try:
                xgb_preds = self._xgb_models[sku_id].predict(self._sales_df)
                xgb_preds["model"] = "xgboost"
            except Exception as e:
                print(f"[Service] XGBoost predict failed for {sku_id}: {e}")

        # Ensemble or fallback to whichever is available
        if prophet_preds is not None and xgb_preds is not None:
            merged = pd.merge(
                prophet_preds.rename(columns={"yhat": "yhat_p", "yhat_lower": "lower_p", "yhat_upper": "upper_p"}),
                xgb_preds.rename(columns={"yhat": "yhat_x", "yhat_lower": "lower_x", "yhat_upper": "upper_x"}),
                on=["ds", "sku_id"], how="inner"
            )
            merged["yhat"]       = ((merged["yhat_p"] + merged["yhat_x"]) / 2).round()
            merged["yhat_lower"] = ((merged["lower_p"] + merged["lower_x"]) / 2).round()
            merged["yhat_upper"] = ((merged["upper_p"] + merged["upper_x"]) / 2).round()
            merged["model"]      = "ensemble"
            return merged[["ds", "yhat", "yhat_lower", "yhat_upper", "model"]].tail(horizon)
        elif prophet_preds is not None:
            return prophet_preds.tail(horizon)
        elif xgb_preds is not None:
            return xgb_preds.tail(horizon)
        else:
            raise ValueError(f"No trained models found for {sku_id}")

    def get_forecast(self, sku_id: str, horizon: int = 30) -> dict:
        self.load()

        if self._sales_df is None:
            raise ValueError("Sales data not loaded")

        sku_meta = self._sku_meta.get(sku_id)
        if not sku_meta:
            raise ValueError(f"SKU {sku_id} not found")

        # Attempt to use precomputed forecasts if horizon is 30 or less and within available models
        if horizon <= 30 and self._forecasts_df is not None:
            precomputed = self._forecasts_df[self._forecasts_df["sku_id"] == sku_id]
            if not precomputed.empty:
                result = precomputed.head(horizon)
            else:
                result = self._run_models_for_forecast(sku_id, horizon)
        else:
            result = self._run_models_for_forecast(sku_id, horizon)

        # MAPE from metrics report
        mape = None
        if sku_id in self._metrics:
            mape = self._metrics[sku_id].get("best_mape")

        forecast_points = [
            {
                "date":       str(row["ds"])[:10],
                "yhat":       float(row["yhat"]),
                "yhat_lower": float(row["yhat_lower"]),
                "yhat_upper": float(row["yhat_upper"]),
                "model":      row.get("model", "precomputed") if "model" in row else "precomputed",
            }
            for _, row in result.iterrows()
        ]

        return {
            "sku_id":       sku_id,
            "sku_name":     sku_meta["sku_name"],
            "horizon_days": horizon,
            "mape":         mape,
            "forecast":     forecast_points,
        }

    def get_all_forecasts(self, horizon: int = 30) -> list[dict]:
        self.load()
        results = []
        for sku_id in self._trained_skus:
            try:
                results.append(self.get_forecast(sku_id, horizon))
            except Exception as e:
                print(f"[Service] Forecast failed for {sku_id}: {e}")
        return results

    # ── Inventory ─────────────────────────────────────────────────────────────

    def get_inventory_status(self) -> dict:
        self.load()

        # Return cached result if available (computed once per server load)
        if self._inventory_cache is not None:
            return self._inventory_cache

        import sys
        
        # Note: 'smart/src' needs to be in path to import smart modules
        SMART_SRC_PATH = os.environ.get("SMART_SRC_PATH", os.path.join(ML_PIPELINE_PATH, "src"))
        if SMART_SRC_PATH not in sys.path:
            sys.path.insert(0, SMART_SRC_PATH)
        from Reorder import calculate_reorder_for_sku

        items = []
        for sku_id in self._trained_skus:
            meta = self._sku_meta.get(sku_id)
            if not meta:
                continue
            try:
                # Use precomputed forecasts directly (fast path) instead of get_forecast()
                forecast_df = None
                if self._forecasts_df is not None:
                    precomputed = self._forecasts_df[self._forecasts_df["sku_id"] == sku_id]
                    if not precomputed.empty:
                        forecast_df = precomputed.head(30).copy()
                        # Ensure correct column names for Reorder module
                        if "ds" in forecast_df.columns and "date" not in forecast_df.columns:
                            forecast_df = forecast_df.rename(columns={"ds": "date"})

                # Fallback: run models live only if no precomputed forecast
                if forecast_df is None or forecast_df.empty:
                    try:
                        result_df = self._run_models_for_forecast(sku_id, 30)
                        forecast_df = result_df.rename(columns={"ds": "date"}).copy()
                        forecast_df["sku_id"] = sku_id
                    except Exception:
                        continue  # Skip SKUs with no working model

                # Derive baseline stock from historical sales data
                hist_sku = self._sales_df[self._sales_df["sku_id"] == sku_id]
                total_sales = hist_sku["quantity_sold"].sum()
                days_in_data = hist_sku["date"].nunique() if "date" in hist_sku.columns else 365
                avg_daily = float(total_sales / days_in_data) if days_in_data > 0 else 0.0
                dynamic_stock = max(int(avg_daily * 21), 50)

                result = calculate_reorder_for_sku(
                    sku_id=sku_id,
                    sku_name=meta["sku_name"],
                    historical_df=self._sales_df,
                    forecast_df=forecast_df,
                    current_stock=dynamic_stock,
                    lead_time_days=meta["lead_time_days"],
                    service_level_z=1.65,
                )
                items.append({
                    "sku_id":              result.sku_id,
                    "sku_name":            result.sku_name,
                    "current_stock":       result.current_stock,
                    "avg_daily_demand":    result.avg_daily_demand,
                    "reorder_point":       result.reorder_point,
                    "safety_stock":        result.safety_stock,
                    "days_until_stockout": result.days_until_stockout,
                    "stockout_risk":       result.stockout_risk,
                    "forecast_30d":        result.forecast_30d,
                    "lead_time_days":      result.lead_time_days,
                    "suggested_order_qty": result.suggested_order_qty,
                })
            except Exception as e:
                print(f"[Service] Inventory calc failed for {sku_id}: {e}")

        critical = sum(1 for i in items if i["stockout_risk"] == "critical")
        high     = sum(1 for i in items if i["stockout_risk"] == "high")

        self._inventory_cache = {
            "total_skus":     len(items),
            "critical_count": critical,
            "high_count":     high,
            "items":          sorted(items, key=lambda x: x.get("days_until_stockout") or 999),
        }
        return self._inventory_cache

    # ── Purchase Orders ───────────────────────────────────────────────────────

    def get_purchase_orders(self) -> dict:
        self.load()
        inventory = self.get_inventory_status()
        import sys
        
        SMART_SRC_PATH = os.path.join(ML_PIPELINE_PATH, "src")
        if SMART_SRC_PATH not in sys.path:
            sys.path.insert(0, SMART_SRC_PATH)
        from Reorder import ReorderResult, generate_purchase_orders

        reorder_results = [
            ReorderResult(**{k: v for k, v in item.items()}) for item in inventory["items"]
        ]
        po_df = generate_purchase_orders(reorder_results)

        orders = po_df.to_dict("records") if not po_df.empty else []
        critical = sum(1 for o in orders if o.get("priority") == "critical")

        return {
            "total_orders":    len(orders),
            "critical_orders": critical,
            "orders":          orders,
        }

    # ── SKU list ──────────────────────────────────────────────────────────────

    def get_skus(self) -> list[dict]:
        self.load()
        
        # Priority 1: Use detailed metadata from the sales CSV if it was loaded
        if self._sku_meta:
            return [
                {
                    "sku_id": k, 
                    "sku_name": self._sku_meta[k]["sku_name"], 
                    "lead_time_days": self._sku_meta[k]["lead_time_days"]
                }
                for k in self._trained_skus
                if k in self._sku_meta
            ]
            
        # Priority 2: Fallback to the Inventory Cache (from pipeline_summary.csv)
        # This ensures the dashboard works even if the raw dataset is not mounted
        if self._inventory_cache and "items" in self._inventory_cache:
            return [
                {
                    "sku_id": item["sku_id"],
                    "sku_name": item["sku_name"],
                    "lead_time_days": item.get("lead_time_days", 7)
                }
                for item in self._inventory_cache["items"]
            ]
            
        return []

    def get_pipeline_status(self) -> dict:
        self.load()
        avg_mape = None
        if self._metrics:
            mapes = [v["best_mape"] for v in self._metrics.values() if "best_mape" in v and pd.notna(v["best_mape"])]
            if mapes:
                avg_mape = float(round(sum(mapes) / len(mapes), 2))

        # Determine human-readable status
        if hasattr(self, '_is_training') and self._is_training: # Check for _is_training attribute
            current_status = "training"
        elif self._loaded:
            current_status = "done"
        else:
            current_status = "idle"

        return {
            "status":       current_status,
            "last_run":     self._last_run,
            "skus_trained": len(self._trained_skus),
            "total_skus_in_data": len(self._sku_meta),
            "avg_mape":     avg_mape,
            "passed_gate":  avg_mape < 25.0 if avg_mape else None,
        }


    async def sync_to_db(self, db):
        """Persist memory cache to PostgreSQL database using provided AsyncSession."""
        if not self._loaded:
            self.load()
            
        from ..db import CRUD
        print("[Service] Syncing data to database...")
        
        # 1. Sync SKUs from main metadata
        sku_count = 0
        for sku_id, meta in self._sku_meta.items():
            await CRUD.upsert_sku(db, sku_id, meta["sku_name"], meta["lead_time_days"])
            sku_count += 1
        
        # Ensure any SKUs mentioned in inventory cache also exist (just in case they weren't in sales_df)
        if self._inventory_cache:
            for item in self._inventory_cache["items"]:
                await CRUD.upsert_sku(db, item["sku_id"], item["sku_name"], item.get("lead_time_days", 7))
                sku_count += 1
        
        # Flush SKUs first to satisfy foreign key constraints before creating inventory/forecasts
        await db.flush()

        # 2. Sync Inventory/Metrics
        inv_count = 0
        if self._inventory_cache:
            for item in self._inventory_cache["items"]:
                await CRUD.upsert_inventory(db, {
                    "sku_id":              item["sku_id"],
                    "current_stock":       item["current_stock"],
                    "reorder_point":       item["reorder_point"],
                    "safety_stock":        item["safety_stock"],
                    "avg_daily_demand":    item["avg_daily_demand"],
                    "days_until_stockout": item["days_until_stockout"],
                    "stockout_risk":       item["stockout_risk"],
                    "forecast_30d":        item["forecast_30d"],
                })
                inv_count += 1
        
        await db.flush()
        
        # 3. Sync Forecasts (if loaded)
        f_count = 0
        if self._forecasts_df is not None:
            # This might be big, let's group by SKU
            for sku_id in self._forecasts_df["sku_id"].unique():
                sku_f = self._forecasts_df[self._forecasts_df["sku_id"] == sku_id]
                points = [
                    {
                        "date":       pd.to_datetime(row["ds"]).date(),
                        "yhat":       float(row["yhat"]),
                        "yhat_lower": float(row["yhat_lower"]),
                        "yhat_upper": float(row["yhat_upper"]),
                        "model":      row.get("model", "ensemble"),
                    }
                    for _, row in sku_f.iterrows()
                ]
                await CRUD.save_forecasts(db, sku_id, points)
                f_count += 1
        
        # 4. Generate and Sync Purchase Orders
        po_resp = self.get_purchase_orders()
        await CRUD.save_purchase_orders(db, po_resp["orders"])
        
        print(f"[Service] Database sync complete. Synced {sku_count} SKUs, {inv_count} Inventory, {f_count} Forecast sets.")


# Singleton instance
pipeline_service = PipelineService()