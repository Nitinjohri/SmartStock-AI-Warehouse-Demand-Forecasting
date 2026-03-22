"""
app/db/models.py
PostgreSQL table definitions using SQLAlchemy ORM.

Tables:
  - skus              : product master data
  - inventory         : current stock levels
  - forecasts         : ML forecast results per SKU per day
  - purchase_orders   : auto-generated POs
  - pipeline_runs     : audit log of every pipeline execution
"""

from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean,
    DateTime, Date, Text, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class SKU(Base):
    __tablename__ = "skus"

    id             : Mapped[str]   = mapped_column(String(20),  primary_key=True)  # SKU-001
    name           : Mapped[str]   = mapped_column(String(100), nullable=False)
    lead_time_days : Mapped[int]   = mapped_column(Integer,     default=7)
    base_demand    : Mapped[float] = mapped_column(Float,       default=0.0)
    is_active      : Mapped[bool]  = mapped_column(Boolean,     default=True)
    created_at     : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    inventory      = relationship("Inventory",     back_populates="sku", uselist=False)
    forecasts      = relationship("Forecast",      back_populates="sku")
    orders         = relationship("PurchaseOrder", back_populates="sku")


class Inventory(Base):
    __tablename__ = "inventory"

    id                  : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id              : Mapped[str]   = mapped_column(String(20), ForeignKey("skus.id"), nullable=False, unique=True)
    current_stock       : Mapped[int]   = mapped_column(Integer, default=0)
    reorder_point       : Mapped[int]   = mapped_column(Integer, default=0)
    safety_stock        : Mapped[int]   = mapped_column(Integer, default=0)
    avg_daily_demand    : Mapped[float] = mapped_column(Float,   default=0.0)
    days_until_stockout : Mapped[int]   = mapped_column(Integer, nullable=True)
    stockout_risk       : Mapped[str]   = mapped_column(String(10), default="low")  # low/medium/high/critical
    forecast_30d        : Mapped[int]   = mapped_column(Integer, default=0)
    updated_at          : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    sku = relationship("SKU", back_populates="inventory")


class Forecast(Base):
    __tablename__ = "forecasts"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id      : Mapped[str]   = mapped_column(String(20), ForeignKey("skus.id"), nullable=False)
    forecast_date: Mapped[str]  = mapped_column(Date,    nullable=False)
    yhat        : Mapped[float] = mapped_column(Float,   nullable=False)
    yhat_lower  : Mapped[float] = mapped_column(Float,   nullable=False)
    yhat_upper  : Mapped[float] = mapped_column(Float,   nullable=False)
    model       : Mapped[str]   = mapped_column(String(20), default="ensemble")
    created_at  : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    sku = relationship("SKU", back_populates="forecasts")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id                  : Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id              : Mapped[str]  = mapped_column(String(20), ForeignKey("skus.id"), nullable=False)
    order_qty           : Mapped[int]  = mapped_column(Integer,  nullable=False)
    priority            : Mapped[str]  = mapped_column(String(10), default="medium")
    status              : Mapped[str]  = mapped_column(String(20), default="pending")  # pending/approved/sent
    days_until_stockout : Mapped[int]  = mapped_column(Integer, nullable=True)
    current_stock       : Mapped[int]  = mapped_column(Integer, default=0)
    reorder_point       : Mapped[int]  = mapped_column(Integer, default=0)
    forecast_30d        : Mapped[int]  = mapped_column(Integer, default=0)
    approved_at         : Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at          : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    sku = relationship("SKU", back_populates="orders")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id           : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    status       : Mapped[str]   = mapped_column(String(20), default="running")  # running/done/failed
    skus_trained : Mapped[int]   = mapped_column(Integer, default=0)
    avg_mape     : Mapped[float] = mapped_column(Float,   nullable=True)
    passed_gate  : Mapped[bool]  = mapped_column(Boolean, nullable=True)
    error_msg    : Mapped[str]   = mapped_column(Text,    nullable=True)
    started_at   : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    finished_at  : Mapped[datetime] = mapped_column(DateTime, nullable=True)