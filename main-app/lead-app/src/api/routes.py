import asyncio
import traceback
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..lib.minio_client import minio_client
from ..lib.logger import get_logger
from ..models import get_db, async_session
from ..services import JobService, WorkflowService, ws_manager

router = APIRouter()
logger = get_logger("lead-app.routes")


async def run_in_background(coro_func, *args, **kwargs):
    """Run an async function in background with its own database session."""
    task_name = coro_func.__name__ if hasattr(coro_func, '__name__') else str(coro_func)
    logger.info(f"Starting background task: {task_name}")

    async with async_session() as db:
        try:
            service = WorkflowService(db)
            await coro_func(service, *args, **kwargs)
            await db.commit()
            logger.info(f"Background task completed: {task_name}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Background task failed: {task_name}")
            logger.error(f"Error: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise


class CreateJobRequest(BaseModel):
    prompt: str
    config: Optional[dict] = None


class UpdateScriptRequest(BaseModel):
    scenes: Optional[list] = None
    enhanced_prompt: Optional[str] = None
    style: Optional[str] = None


class RegenerateSceneRequest(BaseModel):
    scene_id: int
    feedback: Optional[str] = None


@router.post("/jobs")
async def create_job(request: CreateJobRequest, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.create_job(request.prompt, request.config)
    return {
        "id": str(job.id),
        "status": job.status,
        "original_prompt": job.original_prompt,
        "created_at": job.created_at.isoformat()
    }


@router.get("/jobs")
async def list_jobs(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    jobs = await job_service.get_jobs(limit, offset)
    return [
        {
            "id": str(job.id),
            "status": job.status,
            "original_prompt": job.original_prompt,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    output_url = None
    if job.output_path:
        output_url = minio_client.get_presigned_url(job.output_path)

    return {
        "id": str(job.id),
        "status": job.status,
        "original_prompt": job.original_prompt,
        "script": job.enhanced_script,
        "created_at": job.created_at.isoformat(),
        "approved_at": job.approved_at.isoformat() if job.approved_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "output_url": output_url,
        "steps": [
            {
                "id": str(step.id),
                "step_name": step.step_name,
                "status": step.status,
                "progress": step.progress
            }
            for step in job.steps
        ]
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    deleted = await job_service.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True}


@router.post("/jobs/{job_id}/generate-script")
async def generate_script(job_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def run_script_generation(workflow: WorkflowService, jid: UUID):
        await workflow.generate_script(jid)

    background_tasks.add_task(run_in_background, run_script_generation, job_id)

    return {"message": "Script generation started", "job_id": str(job_id)}


@router.put("/jobs/{job_id}/script")
async def update_script(job_id: UUID, request: UpdateScriptRequest, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.enhanced_script:
        raise HTTPException(status_code=400, detail="No script exists for this job")

    updated_script = job.enhanced_script.copy()

    if request.scenes is not None:
        updated_script["scenes"] = request.scenes
    if request.enhanced_prompt is not None:
        updated_script["enhanced_prompt"] = request.enhanced_prompt
    if request.style is not None:
        updated_script["style"] = request.style

    job = await job_service.update_job_script(job_id, updated_script)

    return {"success": True, "script": job.enhanced_script}


@router.post("/jobs/{job_id}/regenerate-scene")
async def regenerate_scene(job_id: UUID, request: RegenerateSceneRequest, db: AsyncSession = Depends(get_db)):
    workflow = WorkflowService(db)
    result = await workflow.regenerate_scene(job_id, request.scene_id, request.feedback)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "scene": result}


@router.post("/jobs/{job_id}/approve")
async def approve_and_generate(job_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ["script_ready", "draft"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve job in status: {job.status}")

    async def run_generation(workflow: WorkflowService, jid: UUID):
        await workflow.approve_and_generate(jid)

    background_tasks.add_task(run_in_background, run_generation, job_id)

    return {"message": "Generation started", "job_id": str(job_id)}


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Retry a stuck or failed job from its last successful step."""
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    retryable_statuses = ["draft", "script_pending", "script_ready", "approved", "processing", "failed"]
    if job.status not in retryable_statuses:
        raise HTTPException(status_code=400, detail=f"Cannot retry job in status: {job.status}")

    logger.info(f"Retry requested for job {job_id} (status: {job.status})")

    async def run_retry(workflow: WorkflowService, jid: UUID):
        await workflow.retry_job(jid)

    background_tasks.add_task(run_in_background, run_retry, job_id)

    return {"message": "Retry started", "job_id": str(job_id), "previous_status": job.status}


@router.post("/jobs/{job_id}/reset")
async def reset_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Reset a job to draft status for fresh restart."""
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await job_service.update_job_status(job_id, "draft")

    from sqlalchemy import update
    from ..models import Job
    await db.execute(update(Job).where(Job.id == job_id).values(error_message=None))
    await db.commit()

    logger.info(f"Job {job_id} reset to draft status")

    return {"success": True, "job_id": str(job_id), "status": "draft"}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await ws_manager.connect(websocket, job_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
