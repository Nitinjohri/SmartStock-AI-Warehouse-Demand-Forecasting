from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..db import CRUD
from ..schemas.models import ForecastResponse, ForecastPoint

router = APIRouter()


@router.get("/all")
async def forecast_all(
    db: AsyncSession = Depends(get_db),
    horizon: int = Query(default=30, ge=7, le=90, include_in_schema=False)
):
    """Get 30-day demand forecast for all SKUs from the database."""
    try:
        # This is a bit heavy, usually we'd want a separate CRUD for 'all forecasts'
        # but let's implement it by getting all SKUs and then their forecasts
        skus = await CRUD.get_all_skus(db)
        results = []
        for sku in skus:
            f_points = await CRUD.get_forecasts_by_sku(db, sku.id)
            if f_points:
                results.append({
                    "sku_id": sku.id,
                    "sku_name": sku.name,
                    "horizon_days": horizon,
                    "forecast": [
                        ForecastPoint(
                            date=str(p.forecast_date),
                            yhat=p.yhat,
                            yhat_lower=p.yhat_lower,
                            yhat_upper=p.yhat_upper,
                            model=p.model
                        ) for p in f_points[:horizon]
                    ]
                })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{sku_id}", response_model=ForecastResponse)
async def forecast_sku(
    sku_id: str,
    db: AsyncSession = Depends(get_db),
    horizon: int = Query(default=30, ge=7, le=90, description="Forecast horizon in days", include_in_schema=False),
):
    """
    Get demand forecast for a specific SKU from the database.
    """
    try:
        # Get SKU for the name
        sku_res = await db.get(CRUD.SKU, sku_id)
        if not sku_res:
            raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
            
        db_points = await CRUD.get_forecasts_by_sku(db, sku_id)
        
        forecast_points = [
            ForecastPoint(
                date=str(p.forecast_date),
                yhat=p.yhat,
                yhat_lower=p.yhat_lower,
                yhat_upper=p.yhat_upper,
                model=p.model
            ) for p in db_points[:horizon]
        ]
        
        return ForecastResponse(
            sku_id=sku_id,
            sku_name=sku_res.name,
            horizon_days=horizon,
            forecast=forecast_points
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")