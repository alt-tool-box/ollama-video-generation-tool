import sys
import asyncio
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))

from comfyui import comfyui_client
from minio_client import minio_client


async def generate_frames(
    scenes: List[dict],
    job_id: str,
    width: int = 512,
    height: int = 512,
    style: str = "cinematic",
    num_frames: int = 16,
    fps: int = 8
) -> dict:
    """Generate animated video clips for each scene using AnimateDiff.
    
    Each scene produces a short MP4 video clip with actual motion.
    AnimateDiff works best at 512x512 with SD 1.5.
    Default: 16 frames at 8fps = 2 seconds of motion per clip.
    
    The clips can be extended by the video renderer to match the 
    scene's target duration using looping or speed adjustment.
    """
    try:
        results = []
        
        for scene in scenes:
            scene_id = scene["id"]
            prompt = scene["image_prompt"]
            full_prompt = f"{prompt}, {style}, high quality, detailed, smooth motion, animated"
            duration_seconds = scene.get("duration_seconds", 3)
            
            # Calculate frames needed for target duration
            # AnimateDiff typically generates 16 frames (sweet spot for quality)
            # More frames = more VRAM, diminishing quality above 24
            scene_frames = min(num_frames, 24)
            
            try:
                video_data = await comfyui_client.generate_video_clip(
                    prompt=full_prompt,
                    width=width,
                    height=height,
                    num_frames=scene_frames,
                    fps=fps
                )
                
                if not video_data:
                    results.append({
                        "scene_id": scene_id,
                        "success": False,
                        "error": "No video clip generated"
                    })
                    continue
                
                # Store as video clip in MinIO
                object_name = f"media/{job_id}/clips/scene_{scene_id:03d}.mp4"
                minio_client.upload_bytes(
                    video_data, object_name, content_type="video/mp4"
                )
                
                # Calculate the actual clip duration
                clip_duration = scene_frames / fps
                
                results.append({
                    "scene_id": scene_id,
                    "success": True,
                    "clip_path": object_name,
                    "clip_duration": clip_duration,
                    "target_duration": duration_seconds,
                    "num_frames": scene_frames,
                    "fps": fps
                })
                
            except Exception as scene_error:
                results.append({
                    "scene_id": scene_id,
                    "success": False,
                    "error": str(scene_error)
                })
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        return {
            "success": len(failed) == 0,
            "total": len(scenes),
            "completed": len(successful),
            "failed": len(failed),
            "clips": results,
            "generation_type": "animatediff"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
