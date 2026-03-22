
import pandas as pd
import numpy as np


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"]  = df["date"].dt.dayofweek          # 0=Mon
    df["day_of_month"] = df["date"].dt.day
    df["month"]        = df["date"].dt.month
    df["quarter"]      = df["date"].dt.quarter
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    return df


def add_lag_features(df: pd.DataFrame, lags: list[int] = [1, 7, 14, 21, 28]) -> pd.DataFrame:
    df = df.copy().sort_values(["sku_id", "date"])
    for lag in lags:
        df[f"lag_{lag}"] = df.groupby("sku_id")["quantity_sold"].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, windows: list[int] = [7, 14, 30]) -> pd.DataFrame:
    df = df.copy().sort_values(["sku_id", "date"])
    for w in windows:
        df[f"rolling_mean_{w}"] = (
            df.groupby("sku_id")["quantity_sold"]
            .transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        )
        df[f"rolling_std_{w}"] = (
            df.groupby("sku_id")["quantity_sold"]
            .transform(lambda x: x.shift(1).rolling(w, min_periods=1).std().fillna(0))
        )
    return df


def add_prophet_regressors(df: pd.DataFrame) -> pd.DataFrame:
    """Adds extra regressors Prophet will use alongside its built-in trend/seasonality."""
    df = df.copy()
    df["is_weekend_reg"]   = (df["day_of_week"] >= 5).astype(float)
    df["is_promotion_reg"] = df["is_promotion"].astype(float)
    df["month_reg"]        = df["month"].astype(float)
    return df


def build_features(df: pd.DataFrame, drop_na: bool = True) -> pd.DataFrame:
    df = add_calendar_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_prophet_regressors(df)
    if drop_na:
        df = df.dropna()
    return df


XGBOOST_FEATURES = [
    "day_of_week", "day_of_month", "month", "quarter",
    "week_of_year", "is_weekend", "is_month_end", "is_promotion",
    "lag_1", "lag_7", "lag_14", "lag_21", "lag_28",
    "rolling_mean_7", "rolling_mean_14", "rolling_mean_30",
    "rolling_std_7",  "rolling_std_14",  "rolling_std_30",
]

PROPHET_REGRESSORS = ["is_weekend_reg", "is_promotion_reg", "month_reg"]