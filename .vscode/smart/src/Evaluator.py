import pandas as pd
import numpy as np
from typing import Optional


# ── Metrics ──────────────────────────────────────────────────────────────────

def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


# ── Walk-forward CV ───────────────────────────────────────────────────────────

def walk_forward_evaluate(
    forecaster,
    df: pd.DataFrame,
    n_splits: int = 3,
    horizon: int = 30,
    min_train_days: int = 180,
) -> dict:
    """
    Splits time series into n_splits folds.
    Each fold trains on history up to cutoff, evaluates on next `horizon` days.
    Returns averaged metrics across folds.
    """
    sku_df = df[df["sku_id"] == forecaster.sku_id].copy()
    sku_df["date"] = pd.to_datetime(sku_df["date"])
    sku_df = sku_df.sort_values("date")

    total_days = (sku_df["date"].max() - sku_df["date"].min()).days
    fold_size  = (total_days - min_train_days - horizon) // n_splits

    all_metrics = []

    for fold in range(n_splits):
        cutoff_idx = min_train_days + fold * fold_size
        cutoff_date = sku_df["date"].min() + pd.Timedelta(days=cutoff_idx)
        test_end    = cutoff_date + pd.Timedelta(days=horizon)

        train = sku_df[sku_df["date"] <= cutoff_date]
        test  = sku_df[(sku_df["date"] > cutoff_date) & (sku_df["date"] <= test_end)]

        if len(train) < min_train_days or len(test) == 0:
            continue

        try:
            forecaster.train(train)
            preds = forecaster.predict(train)

            pred_dates = pd.to_datetime(preds["ds"])
            test_dates = pd.to_datetime(test["date"])

            merged = pd.merge(
                test[["date", "quantity_sold"]].rename(columns={"date": "ds"}),
                preds[["ds", "yhat"]],
                on="ds", how="inner"
            )

            if merged.empty:
                continue

            y_true = merged["quantity_sold"].values
            y_pred = merged["yhat"].values

            all_metrics.append({
                "fold":  fold,
                "mape":  mape(y_true, y_pred),
                "rmse":  rmse(y_true, y_pred),
                "mae":   mae(y_true, y_pred),
                "n":     len(merged),
            })
        except Exception as e:
            print(f"  [CV] Fold {fold} failed: {e}")
            continue

    if not all_metrics:
        return {"mape": 999, "rmse": 999, "mae": 999, "folds": 0}

    metrics_df = pd.DataFrame(all_metrics)
    return {
        "mape":  round(metrics_df["mape"].mean(), 2),
        "rmse":  round(metrics_df["rmse"].mean(), 2),
        "mae":   round(metrics_df["mae"].mean(), 2),
        "folds": len(all_metrics),
    }


# ── Ensemble ──────────────────────────────────────────────────────────────────

def ensemble_predictions(
    prophet_preds: pd.DataFrame,
    xgb_preds: pd.DataFrame,
    prophet_weight: float = 0.5,
) -> pd.DataFrame:
    """
    Weighted average ensemble of Prophet and XGBoost predictions.
    Default: 50/50. Adjust weight based on CV MAPE results.
    """
    xgb_weight = 1.0 - prophet_weight

    merged = pd.merge(
        prophet_preds.rename(columns={"yhat": "yhat_prophet",
                                      "yhat_lower": "lower_prophet",
                                      "yhat_upper": "upper_prophet"}),
        xgb_preds.rename(columns={"yhat": "yhat_xgb",
                                   "yhat_lower": "lower_xgb",
                                   "yhat_upper": "upper_xgb"}),
        on=["ds", "sku_id"], how="inner"
    )

    merged["yhat"]       = (merged["yhat_prophet"] * prophet_weight + merged["yhat_xgb"] * xgb_weight).round()
    merged["yhat_lower"] = (merged["lower_prophet"] * prophet_weight + merged["lower_xgb"] * xgb_weight).round()
    merged["yhat_upper"] = (merged["upper_prophet"] * prophet_weight + merged["upper_xgb"] * xgb_weight).round()
    merged["model"]      = "ensemble"

    return merged[["ds", "sku_id", "yhat", "yhat_lower", "yhat_upper", "model"]]


# ── Model selection ───────────────────────────────────────────────────────────

def select_best_model(
    prophet_metrics: dict,
    xgb_metrics: dict,
    ensemble_metrics: Optional[dict] = None,
) -> str:
    scores = {
        "prophet":  prophet_metrics["mape"],
        "xgboost":  xgb_metrics["mape"],
    }
    if ensemble_metrics:
        scores["ensemble"] = ensemble_metrics["mape"]

    best = min(scores, key=scores.get)
    print(f"  Model scores (MAPE): {scores} → best: {best}")
    return best