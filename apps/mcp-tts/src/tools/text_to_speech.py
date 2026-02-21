import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))

from tts import tts_client
from minio_client import minio_client


def text_to_speech(
    text: str,
    job_id: str,
    scene_id: int,
    voice: str = "default",
    language: str = "en"
) -> dict:
    try:
        audio_data, duration, error = tts_client.synthesize_to_bytes(text, voice, language)
        
        if error:
            return {"success": False, "error": error}
        
        object_name = f"media/{job_id}/audio/scene_{scene_id:03d}.wav"
        minio_client.upload_bytes(audio_data, object_name, content_type="audio/wav")
        
        return {
            "success": True,
            "audio_path": object_name,
            "duration": duration,
            "presigned_url": minio_client.get_presigned_url(object_name)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def text_to_speech_batch(
    scenes: list,
    job_id: str,
    voice: str = "default",
    language: str = "en"
) -> dict:
    try:
        results = []
        total_duration = 0
        errors = []
        
        for scene in scenes:
            scene_id = scene["id"]
            narration = scene.get("narration", "")
            
            if not narration or narration.strip() == "":
                # No narration for this scene - mark as success with no audio
                results.append({
                    "scene_id": scene_id,
                    "success": True,
                    "audio_path": None,
                    "duration": 0,
                    "skipped": True
                })
                continue
            
            result = text_to_speech(narration, job_id, scene_id, voice, language)
            result["scene_id"] = scene_id
            results.append(result)
            
            if result["success"]:
                total_duration += result.get("duration", 0)
            else:
                errors.append(f"Scene {scene_id}: {result.get('error', 'Unknown error')}")
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        skipped = [r for r in results if r.get("skipped")]
        
        return {
            "success": len(failed) == 0,
            "total": len(scenes),
            "completed": len(successful),
            "failed": len(failed),
            "skipped": len(skipped),
            "total_duration": total_duration,
            "audio_segments": results,
            "errors": errors if errors else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
