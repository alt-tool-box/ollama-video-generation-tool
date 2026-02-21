import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tts import tts_client


def list_voices() -> dict:
    try:
        voices = tts_client.list_voices()
        return {
            "success": True,
            "voices": voices
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
