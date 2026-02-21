import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from render import video_renderer


def add_subtitles(
    job_id: str,
    video_path: str,
    subtitles: List[dict],
    font_size: int = 36,
    font_color: str = "white",
    bg_color: str = "black"
) -> dict:
    return video_renderer.add_subtitles(
        job_id=job_id,
        video_path=video_path,
        subtitles=subtitles,
        font_size=font_size,
        font_color=font_color,
        bg_color=bg_color
    )
