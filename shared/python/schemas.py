from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Ensure this module can be imported both ways


class JobStatus(str, Enum):
    DRAFT = "draft"
    SCRIPT_PENDING = "script_pending"
    SCRIPT_READY = "script_ready"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Scene(BaseModel):
    id: int
    description: str
    image_prompt: str
    duration_seconds: float
    narration: str


class ScriptData(BaseModel):
    enhanced_prompt: str
    scenes: List[Scene]
    total_duration: float
    style: str


class JobCreate(BaseModel):
    prompt: str


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    original_prompt: str
    script: Optional[ScriptData] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_url: Optional[str] = None

    class Config:
        from_attributes = True


class JobStepResponse(BaseModel):
    id: str
    job_id: str
    step_name: str
    status: StepStatus
    progress: int
    output_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScriptUpdate(BaseModel):
    enhanced_prompt: Optional[str] = None
    scenes: Optional[List[Scene]] = None
    style: Optional[str] = None


class ProgressUpdate(BaseModel):
    job_id: str
    step_name: str
    status: StepStatus
    progress: int
    message: Optional[str] = None


class GenerateImageRequest(BaseModel):
    prompt: str
    job_id: str
    scene_id: int
    width: int = 1024
    height: int = 576
    style: str = "cinematic"


class GenerateImageResponse(BaseModel):
    success: bool
    image_path: Optional[str] = None
    error: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    job_id: str
    scene_id: int
    voice: str = "default"


class TTSResponse(BaseModel):
    success: bool
    audio_path: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class RenderVideoRequest(BaseModel):
    job_id: str
    frames: List[dict]
    audio_path: str
    output_format: str = "mp4"
    fps: int = 24
    add_transitions: bool = True


class RenderVideoResponse(BaseModel):
    success: bool
    video_path: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None
