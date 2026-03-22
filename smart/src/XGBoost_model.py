import pandas as pd
import numpy as np
import pickle
import os
from typing import Optional

try:
    import xgboost as xgb
except ImportError:
    raise ImportError("Run: pip install xgboost")

from Feature_engineering import XGBOOST_FEATURES, build_features


class XGBoostForecaster:
    def __init__(
        self,
        sku_id: str,
        horizon_days: int = 30,
        n_estimators: int = 300,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
    ):
        self.sku_id = sku_id
        self.horizon_days = horizon_days
        self.model: Optional[xgb.XGBRegressor] = None
        self._model_params = {
            "n_estimators":     n_estimators,
            "learning_rate":    learning_rate,
            "max_depth":        max_depth,
            "subsample":        subsample,
            "colsample_bytree": colsample_bytree,
            "objective":        "reg:squarederror",
            "random_state":     42,
            "n_jobs":           -1,
        }

    def _filter_sku(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[df["sku_id"] == self.sku_id].copy()

    def train(self, df: pd.DataFrame) -> "XGBoostForecaster":
        sku_df = self._filter_sku(df)
        featured = build_features(sku_df, drop_na=True)

        X = featured[XGBOOST_FEATURES]
        y = featured["quantity_sold"]

        self.model = xgb.XGBRegressor(**self._model_params)
        self.model.fit(X, y, eval_set=[(X, y)], verbose=False)

        print(f"[XGBoost] Trained on SKU {self.sku_id} — {len(X)} rows, {len(XGBOOST_FEATURES)} features")
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Recursive multi-step forecast:
        Uses each predicted value as the next step's lag feature.
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call .train() first.")

        sku_df = self._filter_sku(df).copy()
        sku_df["date"] = pd.to_datetime(sku_df["date"])
        sku_df = sku_df.sort_values("date")

        last_date = sku_df["date"].max()
        predictions = []

        # Start with actual history, extend one day at a time
        history = sku_df.copy()

        for step in range(self.horizon_days):
            next_date = last_date + pd.Timedelta(days=step + 1)

            # Build a one-row future record
            future_row = pd.DataFrame([{
                "date":           next_date,
                "sku_id":         self.sku_id,
                "sku_name":       sku_df["sku_name"].iloc[0],
                "quantity_sold":  0,  # placeholder
                "lead_time_days": sku_df["lead_time_days"].iloc[0],
                "is_promotion":   0,
            }])

            # Only keep the last 60 days to prevent an explosion in O(N) complexity for feature building
            extended = pd.concat([history.tail(60), future_row], ignore_index=True)
            featured  = build_features(extended, drop_na=False)
            last_row  = featured[featured["date"] == next_date]

            if last_row.empty or last_row[XGBOOST_FEATURES].isnull().any(axis=1).all():
                pred = history["quantity_sold"].tail(7).mean()
            else:
                pred = float(self.model.predict(last_row[XGBOOST_FEATURES])[0])

            pred = max(0, round(pred))

            # Feed prediction back as real value for next step's lags
            future_row["quantity_sold"] = pred
            history = pd.concat([history, future_row], ignore_index=True)

            predictions.append({
                "ds":    next_date,
                "sku_id": self.sku_id,
                "yhat":  pred,
            })

        result = pd.DataFrame(predictions)
        # Simple confidence interval: ±15% of prediction
        result["yhat_lower"] = (result["yhat"] * 0.85).round()
        result["yhat_upper"] = (result["yhat"] * 1.15).round()
        return result

    def feature_importance(self) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("Model not trained.")
        scores = self.model.feature_importances_
        return pd.DataFrame({
            "feature":    XGBOOST_FEATURES,
            "importance": scores
        }).sort_values("importance", ascending=False)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[XGBoost] Saved → {path}")

    @staticmethod
    def load(path: str) -> "XGBoostForecaster":
        with open(path, "rb") as f:
            return pickle.load(f)