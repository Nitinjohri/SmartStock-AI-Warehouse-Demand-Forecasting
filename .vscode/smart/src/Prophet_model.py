import pandas as pd
import numpy as np
import pickle
import os
from typing import Optional

try:
    from prophet import Prophet
except ImportError:
    raise ImportError("Run: pip install prophet")

from Feature_engineering import PROPHET_REGRESSORS


class ProphetForecaster:
    def __init__(
        self,
        sku_id: str,
        seasonality_mode: str = "multiplicative",
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        horizon_days: int = 30,
    ):
        self.sku_id = sku_id
        self.horizon_days = horizon_days
        self.model: Optional[Prophet] = None
        self._model_params = {
            "seasonality_mode": seasonality_mode,
            "changepoint_prior_scale": changepoint_prior_scale,
            "seasonality_prior_scale": seasonality_prior_scale,
            "weekly_seasonality": True,
            "yearly_seasonality": True,
            "daily_seasonality": False,
        }

    def _build_model(self) -> Prophet:
        m = Prophet(**self._model_params)
        for reg in PROPHET_REGRESSORS:
            m.add_regressor(reg)
        return m

    def _to_prophet_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns to Prophet's expected ds/y format."""
        pdf = df[df["sku_id"] == self.sku_id].copy()
        pdf = pdf.rename(columns={"date": "ds", "quantity_sold": "y"})
        pdf["ds"] = pd.to_datetime(pdf["ds"])
        pdf = pdf[["ds", "y"] + PROPHET_REGRESSORS].sort_values("ds")
        # Drop rows where target is NaN (from lag/rolling feature engineering)
        pdf = pdf.dropna(subset=["y"])
        # Fill NaN in regressors so Prophet doesn't choke
        for reg in PROPHET_REGRESSORS:
            pdf[reg] = pdf[reg].fillna(0)
        return pdf

    def train(self, df: pd.DataFrame) -> "ProphetForecaster":
        pdf = self._to_prophet_df(df)
        if len(pdf) < 2:
            print(f"[Prophet] SKIPPED SKU {self.sku_id} — only {len(pdf)} usable rows (need ≥ 2)")
            return self
        self.model = self._build_model()
        self.model.fit(pdf)
        print(f"[Prophet] Trained on SKU {self.sku_id} — {len(pdf)} rows")
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("Model not trained. Call .train() first.")

        pdf = self._to_prophet_df(df)
        future = self.model.make_future_dataframe(periods=self.horizon_days, freq="D")

        # Extend regressors into the future (carry last known values)
        last_row = pdf.iloc[-1]
        for reg in PROPHET_REGRESSORS:
            future[reg] = future["ds"].apply(
                lambda d: pdf.loc[pdf["ds"] <= d, reg].iloc[-1]
                if not pdf.loc[pdf["ds"] <= d, reg].empty
                else last_row[reg]
            )

        forecast = self.model.predict(future)
        forecast["sku_id"] = self.sku_id
        forecast["yhat"] = forecast["yhat"].clip(lower=0).round()
        forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0).round()
        forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0).round()

        return forecast[["ds", "sku_id", "yhat", "yhat_lower", "yhat_upper"]].tail(
            self.horizon_days
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[Prophet] Saved → {path}")

    @staticmethod
    def load(path: str) -> "ProphetForecaster":
        with open(path, "rb") as f:
            return pickle.load(f)