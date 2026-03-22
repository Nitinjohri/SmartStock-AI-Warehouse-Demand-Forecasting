from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..db import CRUD
from ..schemas.models import PurchaseOrderResponse, PurchaseOrder

router = APIRouter()


@router.get("", response_model=PurchaseOrderResponse)
async def get_purchase_orders(db: AsyncSession = Depends(get_db)):
    """
    Get all auto-generated purchase orders from the database.
    """
    try:
        db_orders = await CRUD.get_all_orders(db)
        
        orders = []
        critical_count = 0
        
        for o in db_orders:
            order = PurchaseOrder(
                sku_id=o.sku_id,
                sku_name=o.sku.name if o.sku else "Unknown",
                order_qty=o.order_qty,
                priority=o.priority,
                days_until_stockout=o.days_until_stockout,
                current_stock=o.current_stock,
                reorder_point=o.reorder_point,
                forecast_30d=o.forecast_30d
            )
            orders.append(order)
            if o.priority == "critical":
                critical_count += 1
                
        return PurchaseOrderResponse(
            total_orders=len(orders),
            critical_orders=critical_count,
            orders=orders
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/critical", response_model=PurchaseOrderResponse)
async def get_critical_orders(db: AsyncSession = Depends(get_db)):
    """Get only CRITICAL priority purchase orders from the database."""
    try:
        all_res = await get_purchase_orders(db)
        critical = [o for o in all_res.orders if o.priority == "critical"]
        return PurchaseOrderResponse(
            total_orders=len(critical),
            critical_orders=len(critical),
            orders=critical
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))