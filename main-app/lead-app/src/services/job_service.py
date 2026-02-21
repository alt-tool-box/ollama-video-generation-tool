from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Job, JobStep, Script, Asset


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_job(self, prompt: str, config: dict = None) -> Job:
        job = Job(
            original_prompt=prompt,
            status="draft",
            config=config or {}
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job
    
    async def get_job(self, job_id: UUID) -> Optional[Job]:
        result = await self.db.execute(
            select(Job)
            .options(selectinload(Job.steps), selectinload(Job.scripts), selectinload(Job.assets))
            .where(Job.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_jobs(self, limit: int = 50, offset: int = 0) -> List[Job]:
        result = await self.db.execute(
            select(Job)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def update_job_status(self, job_id: UUID, status: str, error_message: str = None) -> Job:
        update_data = {"status": status}
        
        if status == "approved":
            update_data["approved_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        elif status == "failed" and error_message:
            update_data["error_message"] = error_message
        
        await self.db.execute(
            update(Job).where(Job.id == job_id).values(**update_data)
        )
        await self.db.commit()
        return await self.get_job(job_id)
    
    async def update_job_script(self, job_id: UUID, script_data: dict) -> Job:
        await self.db.execute(
            update(Job).where(Job.id == job_id).values(enhanced_script=script_data)
        )
        await self.db.commit()
        return await self.get_job(job_id)
    
    async def update_job_output(self, job_id: UUID, output_path: str) -> Job:
        await self.db.execute(
            update(Job).where(Job.id == job_id).values(output_path=output_path)
        )
        await self.db.commit()
        return await self.get_job(job_id)
    
    async def create_script(self, job_id: UUID, enhanced_prompt: str, scenes: list,
                           total_duration: int, style: str) -> Script:
        # Get the latest version number for this job's scripts
        existing = await self.db.execute(
            select(Script).where(Script.job_id == job_id).order_by(Script.version.desc()).limit(1)
        )
        latest = existing.scalars().first()
        version = (latest.version + 1) if latest else 1
        
        script = Script(
            job_id=job_id,
            version=version,
            enhanced_prompt=enhanced_prompt,
            scenes=scenes,
            total_duration=total_duration,
            style=style
        )
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        return script
    
    async def approve_script(self, job_id: UUID, script_id: UUID) -> Script:
        await self.db.execute(
            update(Script).where(Script.id == script_id).values(is_approved=True)
        )
        await self.db.commit()
        
        result = await self.db.execute(select(Script).where(Script.id == script_id))
        return result.scalar_one_or_none()
    
    async def create_job_step(self, job_id: UUID, step_name: str) -> JobStep:
        step = JobStep(
            job_id=job_id,
            step_name=step_name,
            status="pending"
        )
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step
    
    async def update_job_step(self, step_id: UUID, status: str, progress: int = None,
                             output_path: str = None, error_message: str = None) -> JobStep:
        update_data = {"status": status}
        
        if progress is not None:
            update_data["progress"] = progress
        if output_path:
            update_data["output_path"] = output_path
        if error_message:
            update_data["error_message"] = error_message
        if status == "in_progress":
            update_data["started_at"] = datetime.utcnow()
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.utcnow()
        
        await self.db.execute(
            update(JobStep).where(JobStep.id == step_id).values(**update_data)
        )
        await self.db.commit()
        
        result = await self.db.execute(select(JobStep).where(JobStep.id == step_id))
        return result.scalar_one_or_none()
    
    async def create_asset(self, job_id: UUID, asset_type: str, minio_path: str,
                          asset_metadata: dict = None) -> Asset:
        asset = Asset(
            job_id=job_id,
            asset_type=asset_type,
            minio_path=minio_path,
            asset_metadata=asset_metadata or {}
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset
    
    async def delete_job(self, job_id: UUID) -> bool:
        job = await self.get_job(job_id)
        if job:
            await self.db.delete(job)
            await self.db.commit()
            return True
        return False
