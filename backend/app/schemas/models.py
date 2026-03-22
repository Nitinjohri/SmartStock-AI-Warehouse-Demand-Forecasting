"""
schemas/models.py
All Pydantic request/response schemas for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ── Forecast ──────────────────────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    date:        str
    yhat:        float = Field(..., description="Predicted demand")
    yhat_lower:  float = Field(..., description="Lower confidence bound")
    yhat_upper:  float = Field(..., description="Upper confidence bound")
    model:       str   = Field(..., description="prophet | xgboost | ensemble")

class ForecastResponse(BaseModel):
    sku_id:       str
    sku_name:     str
    horizon_days: int
    mape:         Optional[float] = None
    forecast:     list[ForecastPoint]


# ── Inventory ─────────────────────────────────────────────────────────────────

class SKUSummary(BaseModel):
    sku_id:            str
    sku_name:          str
    current_stock:     int
    avg_daily_demand:  float
    reorder_point:     int
    safety_stock:      int
    days_until_stockout: Optional[int]
    stockout_risk:     str   # low | medium | high | critical
    forecast_30d:      int

class InventoryResponse(BaseModel):
    total_skus:      int
    critical_count:  int
    high_count:      int
    items:           list[SKUSummary]


# ── Purchase Orders ───────────────────────────────────────────────────────────

class PurchaseOrder(BaseModel):
    sku_id:              str
    sku_name:            str
    order_qty:           int
    priority:            str
    days_until_stockout: Optional[int]
    current_stock:       int
    reorder_point:       int
    forecast_30d:        int

class PurchaseOrderResponse(BaseModel):
    total_orders:    int
    critical_orders: int
    orders:          list[PurchaseOrder]


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineStatus(BaseModel):
    status:       str   # idle | running | done | failed
    last_run:     Optional[str]
    skus_trained: int
    avg_mape:     Optional[float]
    passed_gate:  Optional[bool]