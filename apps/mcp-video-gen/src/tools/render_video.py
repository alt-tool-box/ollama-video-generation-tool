import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from render import video_renderer


def render_video(
    job_id: str,
    frames: List[dict],
    audio_path: str = None,
    fps: int = 24,
    add_transitions: bool = True,
    transition_duration: float = 0.5
) -> dict:
    return video_renderer.render_video(
        job_id=job_id,
        frames=frames,
        audio_path=audio_path,
        fps=fps,
        add_transitions=add_transitions,
        transition_duration=transition_duration
    )
