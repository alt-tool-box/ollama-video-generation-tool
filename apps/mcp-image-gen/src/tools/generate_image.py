import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))

from comfyui import comfyui_client
from minio_client import minio_client


async def generate_image(
    prompt: str,
    job_id: str,
    scene_id: int,
    width: int = 1024,
    height: int = 576,
    style: str = "cinematic"
) -> dict:
    """Generate a single static image (legacy SDXL method)."""
    try:
        full_prompt = f"{prompt}, {style}, high quality, detailed"
        
        image_data = await comfyui_client.generate_image(full_prompt, width, height)
        
        if not image_data:
            return {"success": False, "error": "No image generated"}
        
        object_name = f"media/{job_id}/frames/scene_{scene_id:03d}.png"
        minio_client.upload_bytes(image_data, object_name, content_type="image/png")
        
        return {
            "success": True,
            "image_path": object_name,
            "presigned_url": minio_client.get_presigned_url(object_name)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def generate_video_clip(
    prompt: str,
    job_id: str,
    scene_id: int,
    width: int = 512,
    height: int = 512,
    style: str = "cinematic",
    num_frames: int = 16,
    fps: int = 8
) -> dict:
    """Generate a single animated video clip using AnimateDiff."""
    try:
        full_prompt = f"{prompt}, {style}, high quality, detailed, smooth motion, animated"
        
        video_data = await comfyui_client.generate_video_clip(
            prompt=full_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            fps=fps
        )
        
        if not video_data:
            return {"success": False, "error": "No video clip generated"}
        
        object_name = f"media/{job_id}/clips/scene_{scene_id:03d}.mp4"
        minio_client.upload_bytes(video_data, object_name, content_type="video/mp4")
        
        clip_duration = num_frames / fps
        
        return {
            "success": True,
            "clip_path": object_name,
            "clip_duration": clip_duration,
            "num_frames": num_frames,
            "fps": fps,
            "presigned_url": minio_client.get_presigned_url(object_name)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
