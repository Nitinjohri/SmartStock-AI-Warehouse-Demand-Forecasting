"""
app/db/crud.py
Database read/write operations.
Called by routers to persist and retrieve data.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from .models import SKU, Inventory, Forecast, PurchaseOrder, PipelineRun


# ── SKUs ──────────────────────────────────────────────────────────────────────

async def upsert_sku(db: AsyncSession, sku_id: str, name: str, lead_time: int) -> SKU:
    result = await db.execute(select(SKU).where(SKU.id == sku_id))
    sku = result.scalar_one_or_none()
    if sku:
        sku.name = name
        sku.lead_time_days = lead_time
    else:
        sku = SKU(id=sku_id, name=name, lead_time_days=lead_time)
        db.add(sku)
    return sku

async def get_all_skus(db: AsyncSession) -> list[SKU]:
    result = await db.execute(select(SKU).where(SKU.is_active))
    return result.scalars().all()


# ── Inventory ─────────────────────────────────────────────────────────────────

async def upsert_inventory(db: AsyncSession, data: dict) -> Inventory:
    result = await db.execute(select(Inventory).where(Inventory.sku_id == data["sku_id"]))
    inv = result.scalar_one_or_none()
    if inv:
        for k, v in data.items():
            setattr(inv, k, v)
    else:
        inv = Inventory(**data)
        db.add(inv)
    return inv

async def get_all_inventory(db: AsyncSession) -> list[Inventory]:
    result = await db.execute(select(Inventory).options(selectinload(Inventory.sku)))
    return result.scalars().all()

async def get_inventory_by_sku(db: AsyncSession, sku_id: str) -> Inventory | None:
    result = await db.execute(
        select(Inventory)
        .where(Inventory.sku_id == sku_id)
        .options(selectinload(Inventory.sku))
    )
    return result.scalar_one_or_none()


# ── Forecasts ─────────────────────────────────────────────────────────────────

async def save_forecasts(db: AsyncSession, sku_id: str, forecast_points: list[dict]):
    """Delete old forecasts for SKU and insert new ones."""
    await db.execute(delete(Forecast).where(Forecast.sku_id == sku_id))
    from datetime import date, datetime

    for point in forecast_points:
        f_date = point["date"]
        # Convert string date to date object if needed
        if isinstance(f_date, str):
            try:
                f_date = date.fromisoformat(f_date[:10])
            except ValueError:
                continue # Skip invalid dates
        elif isinstance(f_date, datetime):
            f_date = f_date.date()

        try:
            db.add(Forecast(
                sku_id=sku_id,
                forecast_date=f_date,
                yhat=float(point["yhat"]),
                yhat_lower=float(point["yhat_lower"]),
                yhat_upper=float(point["yhat_upper"]),
                model=point.get("model", "ensemble"),
            ))
        except (ValueError, TypeError):
            continue # Skip rows with invalid numbers

async def get_forecasts_by_sku(db: AsyncSession, sku_id: str) -> list[Forecast]:
    result = await db.execute(
        select(Forecast)
        .where(Forecast.sku_id == sku_id)
        .order_by(Forecast.forecast_date)
    )
    return result.scalars().all()


# ── Purchase Orders ───────────────────────────────────────────────────────────

async def save_purchase_orders(db: AsyncSession, orders: list[dict]):
    """Clear pending orders and insert fresh ones."""
    await db.execute(delete(PurchaseOrder).where(PurchaseOrder.status == "pending"))
    
    # Valid columns for PurchaseOrder
    valid_cols = {
        "sku_id", "order_qty", "priority", "status", 
        "days_until_stockout", "current_stock", "reorder_point", "forecast_30d"
    }

    for order_data in orders:
        filtered_data = {k: v for k, v in order_data.items() if k in valid_cols}
        
        # Ensure numeric types
        for col in ["order_qty", "days_until_stockout", "current_stock", "reorder_point", "forecast_30d"]:
            if col in filtered_data and filtered_data[col] is not None:
                try:
                    filtered_data[col] = int(float(filtered_data[col]))
                except (ValueError, TypeError):
                    filtered_data[col] = 0
                    
        db.add(PurchaseOrder(**filtered_data))

async def get_all_orders(db: AsyncSession) -> list[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.sku))
        .order_by(PurchaseOrder.priority, PurchaseOrder.created_at.desc())
    )
    return result.scalars().all()

async def approve_order(db: AsyncSession, order_id: int) -> PurchaseOrder | None:
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = "approved"
        order.approved_at = datetime.utcnow()
    return order


# ── Pipeline Runs ─────────────────────────────────────────────────────────────

async def create_pipeline_run(db: AsyncSession) -> PipelineRun:
    run = PipelineRun(status="running")
    db.add(run)
    await db.flush()
    return run

async def finish_pipeline_run(db: AsyncSession, run_id: int, passed: bool, avg_mape: float, skus: int):
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()
    if run:
        run.status      = "done" if passed else "failed"
        run.passed_gate = passed
        run.avg_mape    = avg_mape
        run.skus_trained = skus
        run.finished_at  = datetime.utcnow()

async def get_latest_pipeline_run(db: AsyncSession) -> PipelineRun | None:
    result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()