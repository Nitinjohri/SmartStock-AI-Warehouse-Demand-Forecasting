from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from .app.db.database import init_db

from .app.routers import forecast, inventory, orders, health
from .app.services.pipeline_service import pipeline_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models and data at startup
    print("[Server] Starting up - loading ML service...")
    await init_db()       # create tables on startup
    try:
        # Run load in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, pipeline_service.load)
        print("[Server] ML service ready. Syncing to DB...")
        
        # Sync the loaded data to the database
        from .app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await pipeline_service.sync_to_db(db)
            await db.commit()
            
        print("[Server] Initial database sync complete.")
    except Exception as e:
        print(f"[Server] Startup load/sync failed: {e}")
    yield
    print("[Server] Shutting down...")

app = FastAPI(
    title="SmartStock AI",
    description="Warehouse Demand Forecasting & Auto-Replenishment API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React frontend (localhost:3000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router,    tags=["Health"])
app.include_router(forecast.router,  prefix="/forecast",  tags=["Forecast"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(orders.router,    prefix="/orders",    tags=["Purchase Orders"])