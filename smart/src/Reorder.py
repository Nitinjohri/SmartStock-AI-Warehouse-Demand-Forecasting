import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReorderResult:
    sku_id: str
    sku_name: str
    current_stock: int
    avg_daily_demand: float
    lead_time_days: int
    safety_stock: int
    reorder_point: int
    suggested_order_qty: int
    days_until_stockout: Optional[int]
    stockout_risk: str          # "low" | "medium" | "high" | "critical"
    forecast_30d: int


def calculate_safety_stock(
    daily_demands: np.ndarray,
    lead_time_days: int,
    service_level_z: float = 1.65,   # 95% service level
) -> int:
    """
    Safety stock = Z × σ_demand × √lead_time
    Z=1.65 → 95% service level, Z=2.05 → 98%, Z=2.33 → 99%
    """
    std_demand = np.std(daily_demands)
    safety = service_level_z * std_demand * np.sqrt(lead_time_days)
    return int(np.ceil(safety))


def calculate_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: int,
) -> int:
    """Reorder Point = avg_daily_demand × lead_time + safety_stock"""
    return int(np.ceil(avg_daily_demand * lead_time_days + safety_stock))


def assess_stockout_risk(
    current_stock: int,
    reorder_point: int,
    avg_daily_demand: float,
) -> tuple[Optional[int], str]:
    if avg_daily_demand <= 0:
        return None, "low"

    days_until_stockout = int(current_stock / avg_daily_demand)

    ratio = current_stock / max(reorder_point, 1)
    if ratio < 0.5 or days_until_stockout <= 3:
        risk = "critical"
    elif ratio < 0.8 or days_until_stockout <= 7:
        risk = "high"
    elif ratio < 1.0 or days_until_stockout <= 14:
        risk = "medium"
    else:
        risk = "low"

    return days_until_stockout, risk


def calculate_reorder_for_sku(
    sku_id: str,
    sku_name: str,
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    current_stock: int,
    lead_time_days: int,
    service_level_z: float = 1.65,
) -> ReorderResult:
    hist = historical_df[historical_df["sku_id"] == sku_id]
    fcast = forecast_df[forecast_df["sku_id"] == sku_id]

    daily_demands = hist["quantity_sold"].values
    avg_daily = float(np.mean(daily_demands)) if len(daily_demands) > 0 else 0.0

    safety = calculate_safety_stock(daily_demands, lead_time_days, service_level_z)
    rop = calculate_reorder_point(avg_daily, lead_time_days, safety)

    days_until_stockout, risk = assess_stockout_risk(current_stock, rop, avg_daily)

    # Economic Order Quantity (EOQ) simplified: order 30-day forecast quantity
    forecast_30d = int(fcast["yhat"].sum()) if not fcast.empty else int(avg_daily * 30)
    # Round up to nearest 10 for practical ordering
    suggested_qty = max(int(np.ceil(forecast_30d / 10) * 10), int(safety * 2))

    return ReorderResult(
        sku_id=sku_id,
        sku_name=sku_name,
        current_stock=current_stock,
        avg_daily_demand=round(avg_daily, 1),
        lead_time_days=lead_time_days,
        safety_stock=safety,
        reorder_point=rop,
        suggested_order_qty=suggested_qty,
        days_until_stockout=days_until_stockout,
        stockout_risk=risk,
        forecast_30d=forecast_30d,
    )


def generate_purchase_orders(results: list[ReorderResult]) -> pd.DataFrame:
    """Convert reorder results into actionable PO rows."""
    rows = []
    for r in results:
        if r.stockout_risk in ("high", "critical") or r.current_stock <= r.reorder_point:
            rows.append({
                "sku_id":           r.sku_id,
                "sku_name":         r.sku_name,
                "order_qty":        r.suggested_order_qty,
                "priority":         r.stockout_risk,
                "days_until_stockout": r.days_until_stockout,
                "current_stock":    r.current_stock,
                "reorder_point":    r.reorder_point,
                "forecast_30d":     r.forecast_30d,
            })
    return pd.DataFrame(rows).sort_values(
        "days_until_stockout", na_position="last"
    ) if rows else pd.DataFrame()