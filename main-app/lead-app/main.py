from src.lib.logger import get_logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update
import uvicorn

from src.api import router
from src.models import init_db, async_session, Job
from src.lib.config import config

logger = get_logger("lead-app.main")

app = FastAPI(
    title="Video Creation API",
    description="AI-powered video creation orchestrator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


async def recover_orphaned_jobs():
    """Mark jobs stuck in processing states as interrupted on startup."""
    orphaned_statuses = ["script_pending", "approved", "processing"]

    async with async_session() as db:
        result = await db.execute(
            select(Job).where(Job.status.in_(orphaned_statuses))
        )
        orphaned_jobs = result.scalars().all()

        if orphaned_jobs:
            logger.warning(f"Found {len(orphaned_jobs)} orphaned jobs on startup")

            for job in orphaned_jobs:
                logger.info(f"Marking job {job.id} as interrupted (was: {job.status})")
                await db.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(
                        status="failed",
                        error_message=f"Job was interrupted due to server restart. Previous status: {job.status}. Use retry to resume."
                    )
                )

            await db.commit()
            logger.info(f"Marked {len(orphaned_jobs)} jobs as interrupted")
        else:
            logger.info("No orphaned jobs found on startup")


@app.on_event("startup")
async def startup():
    logger.info("Starting Video Creation API...")
    await init_db()
    logger.info("Database initialized")
    await recover_orphaned_jobs()
    logger.info("Startup complete")


@app.get("/")
async def root():
    return {"message": "Video Creation API", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.LEAD_APP_PORT,
        reload=True
    )
