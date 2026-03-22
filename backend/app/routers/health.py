import subprocess
import os
import threading
from fastapi import APIRouter, BackgroundTasks, Query
from ..services.pipeline_service import pipeline_service, ML_PIPELINE_PATH

router = APIRouter()

def run_ml_pipeline_task(max_skus: int = 10):
    """Background task to run the ML pipeline training script."""
    print(f"[Background] Starting ML pipeline for {'all' if max_skus == 0 else f'top {max_skus}'} SKUs...")
    pipeline_service._is_training = True
    try:
        # Construct the absolute path to pipeline.py from the project root using CWD
        cwd = os.getcwd()
        if os.path.basename(cwd) == "backend" or os.path.basename(cwd) == "app":
            project_root = os.path.abspath(os.path.join(cwd, ".."))
        else:
            project_root = cwd
            
        pipeline_script = os.path.join(project_root, "smart", "src", "pipeline.py")
        
        # Determine the correct python executable depending on virtual environment
        python_executable = os.path.join(project_root, "smart", "Scripts", "python")
        if not os.path.exists(python_executable + ".exe"): # Handle cases when venv doesn't exist yet
            python_executable = "python"
        
        print(f"[Background] Running: {python_executable} {pipeline_script}")
        
        # Ensure we use UTF-8 encoding in the subprocess to prevent 'charmap' errors on Windows
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        if max_skus > 0:
            env["MAX_SKUS"] = str(max_skus)
        
        # Run using subprocess (using the smart virtual environment's python)
        result = subprocess.run(
            [python_executable, pipeline_script],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            encoding="utf-8"
        )
        
        if result.stdout:
            print("[Background] Subprocess stdout snippet:")
            print("\n".join(result.stdout.splitlines()[-10:])) # Show last 10 lines
            
        print("[Background] ML pipeline finished successfully.")
        
        # Reload the newly generated models into the service memory
        pipeline_service._loaded = False
        pipeline_service.load()
        
        # Sync to DB
        import asyncio
        from ..db.database import AsyncSessionLocal
        async def sync():
            async with AsyncSessionLocal() as db:
                await pipeline_service.sync_to_db(db)
                await db.commit()
        asyncio.run(sync())
        
        from datetime import datetime
        pipeline_service._last_run = datetime.now().isoformat()
        
    except subprocess.CalledProcessError as e:
        print("[Background] ML pipeline FAILED:")
        print(e.stderr if e.stderr else e.stdout)
    except Exception as e:
        print(f"[Background] Unexpected error running ML pipeline: {e}")
    finally:
        pipeline_service._is_training = False

@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/skus")
def get_skus():
    return pipeline_service.get_skus()


@router.get("/pipeline/status")
def pipeline_status():
    return pipeline_service.get_pipeline_status()


@router.post("/pipeline/load")
async def load_models_memory():
    """
    Manually load the trained models and sales data into memory from Swagger UI.
    (Note: If the frontend requests data first, it will automatically load on its own).
    """
    import asyncio
    await asyncio.to_thread(pipeline_service.load)
    return {"status": "success", "message": "Models and data loaded into memory successfully!"}


@router.post("/pipeline/run")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    max_skus: int = Query(default=100, ge=0, le=5000, description="Limit training to the top N SKUs. Set to 0 to train ALL 2,000+ SKUs (takes 1-2 hours).")
):
    """
    Trigger the ML training pipeline in the background.
    Returns immediately while the pipeline trains new models and saves outputs.
    """
    background_tasks.add_task(run_ml_pipeline_task, max_skus)
    return {"message": f"ML pipeline training started in the background for {'all' if max_skus == 0 else f'top {max_skus}'} SKUs. Check /pipeline/status for updates."}