from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..db import CRUD
from ..schemas.models import InventoryResponse, SKUSummary

router = APIRouter()


@router.get("", response_model=InventoryResponse)
async def get_inventory(db: AsyncSession = Depends(get_db)):
    """
    Get current inventory status for all SKUs from the database.
    """
    try:
        inventory_items = await CRUD.get_all_inventory(db)
        
        # Format for schema
        items = []
        critical_count = 0
        high_count = 0
        
        for inv in inventory_items:
            # We need the SKU name, which is related
            # In an ideal world, we'd join in the query, but let's use the relationship
            sku_name = inv.sku.name if inv.sku else "Unknown"
            
            summary = SKUSummary(
                sku_id=inv.sku_id,
                sku_name=sku_name,
                current_stock=inv.current_stock,
                avg_daily_demand=inv.avg_daily_demand,
                reorder_point=inv.reorder_point,
                safety_stock=inv.safety_stock,
                days_until_stockout=inv.days_until_stockout,
                stockout_risk=inv.stockout_risk,
                forecast_30d=inv.forecast_30d
            )
            items.append(summary)
            if inv.stockout_risk == "critical":
                critical_count += 1
            elif inv.stockout_risk == "high":
                high_count += 1
                
        return InventoryResponse(
            total_skus=len(items),
            critical_count=critical_count,
            high_count=high_count,
            items=items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{sku_id}", response_model=SKUSummary)
async def get_sku_inventory(sku_id: str, db: AsyncSession = Depends(get_db)):
    """Get inventory status for a single SKU from the database."""
    try:
        inv = await CRUD.get_inventory_by_sku(db, sku_id)
        if not inv:
            raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
            
        return SKUSummary(
            sku_id=inv.sku_id,
            sku_name=inv.sku.name if inv.sku else "Unknown",
            current_stock=inv.current_stock,
            avg_daily_demand=inv.avg_daily_demand,
            reorder_point=inv.reorder_point,
            safety_stock=inv.safety_stock,
            days_until_stockout=inv.days_until_stockout,
            stockout_risk=inv.stockout_risk,
            forecast_30d=inv.forecast_30d
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")