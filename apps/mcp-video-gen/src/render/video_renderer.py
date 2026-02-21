import os
import tempfile
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))

# MoviePy 2.x has different import structure than 1.x
try:
    # MoviePy 2.x imports
    from moviepy import (
        ImageClip, AudioFileClip, CompositeAudioClip,
        concatenate_videoclips, CompositeVideoClip, TextClip, VideoFileClip
    )
    from moviepy.video.fx import FadeIn, FadeOut
    MOVIEPY_V2 = True
except ImportError:
    # MoviePy 1.x imports
    from moviepy.editor import (
        ImageClip,
        AudioFileClip,
        CompositeAudioClip,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        VideoFileClip
    )
    from moviepy.video.fx.all import fadein, fadeout
    MOVIEPY_V2 = False

from minio_client import minio_client


def apply_fadein(clip, duration):
    """Apply fade in effect compatible with both moviepy versions."""
    if MOVIEPY_V2:
        return clip.with_effects([FadeIn(duration)])
    else:
        return clip.fx(fadein, duration)


def apply_fadeout(clip, duration):
    """Apply fade out effect compatible with both moviepy versions."""
    if MOVIEPY_V2:
        return clip.with_effects([FadeOut(duration)])
    else:
        return clip.fx(fadeout, duration)


def set_clip_start(clip, start_time):
    """Set clip start time compatible with both moviepy versions."""
    if MOVIEPY_V2:
        return clip.with_start(start_time)
    else:
        return clip.set_start(start_time)


def set_clip_audio(video_clip, audio_clip):
    """Set audio on video clip compatible with both moviepy versions."""
    if MOVIEPY_V2:
        return video_clip.with_audio(audio_clip)
    else:
        return video_clip.set_audio(audio_clip)


def set_clip_fps(clip, fps):
    """Set clip FPS compatible with both moviepy versions."""
    if MOVIEPY_V2:
        return clip.with_fps(fps)
    else:
        return clip.set_fps(fps)


class VideoRenderer:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def download_asset(self, minio_path: str, local_name: str) -> str:
        local_path = os.path.join(self.temp_dir, local_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        minio_client.download_file(minio_path, local_path)
        return local_path
    
    def _loop_clip_to_duration(self, clip, target_duration: float, fps: int = 24):
        """Loop a video clip to fill the target duration.
        
        If the clip is shorter than target_duration, it will be looped.
        If it's longer, it will be trimmed.
        """
        clip_duration = clip.duration
        
        if clip_duration is None or clip_duration <= 0:
            return clip
        
        if clip_duration >= target_duration:
            # Trim to target duration
            if MOVIEPY_V2:
                return clip.subclipped(0, target_duration)
            else:
                return clip.subclip(0, target_duration)
        
        # Need to loop: repeat the clip enough times to fill target_duration
        num_loops = int(target_duration / clip_duration) + 1
        looped_clips = [clip] * num_loops
        looped = concatenate_videoclips(looped_clips)
        
        # Trim to exact target duration
        if MOVIEPY_V2:
            return looped.subclipped(0, target_duration)
        else:
            return looped.subclip(0, target_duration)
    
    def render_video(
        self,
        job_id: str,
        frames: List[dict],
        audio_path: str = None,
        fps: int = 24,
        add_transitions: bool = True,
        transition_duration: float = 0.5
    ) -> dict:
        """Render final video from video clips (AnimateDiff) or static images.
        
        Each frame dict can have either:
        - 'clip_path': path to a video clip (AnimateDiff output)
        - 'image_path': path to a static image (legacy fallback)
        
        Video clips are looped/trimmed to match the target duration.
        """
        try:
            clips = []
            audio_clips = []
            current_time = 0
            
            for i, frame in enumerate(frames):
                duration = frame.get("duration", 3)
                
                # Determine if this is a video clip or static image
                if frame.get("clip_path"):
                    # AnimateDiff video clip
                    clip_local = self.download_asset(
                        frame["clip_path"],
                        f"clip_{i}.mp4"
                    )
                    raw_clip = VideoFileClip(clip_local)
                    
                    # Loop/trim to match target duration
                    clip = self._loop_clip_to_duration(raw_clip, duration, fps)
                    clip = set_clip_fps(clip, fps)
                    
                elif frame.get("image_path"):
                    # Legacy static image fallback
                    image_path = self.download_asset(
                        frame["image_path"],
                        f"frame_{i}.png"
                    )
                    clip = ImageClip(image_path, duration=duration)
                    clip = set_clip_fps(clip, fps)
                else:
                    continue
                
                # Add transitions
                if add_transitions and len(frames) > 1:
                    if i > 0:
                        clip = apply_fadein(clip, transition_duration)
                    if i < len(frames) - 1:
                        clip = apply_fadeout(clip, transition_duration)
                
                clips.append(clip)
                
                # Handle per-scene audio
                if frame.get("audio_path"):
                    audio_local = self.download_asset(
                        frame["audio_path"],
                        f"audio_{i}.wav"
                    )
                    audio_clip = AudioFileClip(audio_local)
                    audio_clip = set_clip_start(audio_clip, current_time)
                    audio_clips.append(audio_clip)
                
                current_time += duration
            
            if not clips:
                return {"success": False, "error": "No valid clips to render"}
            
            # Concatenate all scene clips
            if add_transitions and len(clips) > 1:
                final_video = concatenate_videoclips(clips, method="compose")
            else:
                final_video = concatenate_videoclips(clips)
            
            # Apply audio
            if audio_clips:
                final_audio = CompositeAudioClip(audio_clips)
                final_video = set_clip_audio(final_video, final_audio)
            elif audio_path:
                full_audio_local = self.download_asset(audio_path, "full_audio.wav")
                full_audio = AudioFileClip(full_audio_local)
                final_video = set_clip_audio(final_video, full_audio)
            
            output_local = os.path.join(self.temp_dir, "output.mp4")
            # Suppress MoviePy progress output to prevent MCP JSON communication issues
            write_kwargs = {
                "fps": fps,
                "codec": "libx264",
                "audio_codec": "aac",
                "preset": "medium",
                "threads": 4,
                "logger": None,  # Disable MoviePy logging to stdout
            }
            # MoviePy 1.x supports 'verbose', 2.x does not
            if not MOVIEPY_V2:
                write_kwargs["verbose"] = False
            final_video.write_videofile(output_local, **write_kwargs)
            
            # Cleanup clips
            final_video.close()
            for clip in clips:
                clip.close()
            for ac in audio_clips:
                ac.close()
            
            output_minio = f"media/{job_id}/output/final.mp4"
            minio_client.upload_file(output_local, output_minio, content_type="video/mp4")
            
            return {
                "success": True,
                "video_path": output_minio,
                "duration": current_time,
                "presigned_url": minio_client.get_presigned_url(output_minio)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_subtitles(
        self,
        job_id: str,
        video_path: str,
        subtitles: List[dict],
        font_size: int = 36,
        font_color: str = "white",
        bg_color: str = "black"
    ) -> dict:
        try:
            video_local = self.download_asset(video_path, "video_for_subs.mp4")
            video = VideoFileClip(video_local)
            
            subtitle_clips = []
            for sub in subtitles:
                txt_clip = TextClip(
                    sub["text"],
                    fontsize=font_size,
                    color=font_color,
                    bg_color=bg_color,
                    font="Arial"
                )
                # MoviePy 2.x uses with_* methods, 1.x uses set_* methods
                if MOVIEPY_V2:
                    txt_clip = txt_clip.with_position(("center", "bottom"))
                    txt_clip = txt_clip.with_start(sub["start"])
                    txt_clip = txt_clip.with_duration(sub["duration"])
                else:
                    txt_clip = txt_clip.set_position(("center", "bottom"))
                    txt_clip = txt_clip.set_start(sub["start"])
                    txt_clip = txt_clip.set_duration(sub["duration"])
                subtitle_clips.append(txt_clip)
            
            final = CompositeVideoClip([video] + subtitle_clips)
            
            output_local = os.path.join(self.temp_dir, "output_subtitled.mp4")
            sub_write_kwargs = {
                "fps": video.fps,
                "codec": "libx264",
                "audio_codec": "aac",
                "logger": None,
            }
            if not MOVIEPY_V2:
                sub_write_kwargs["verbose"] = False
            final.write_videofile(output_local, **sub_write_kwargs)
            
            final.close()
            video.close()
            
            output_minio = f"media/{job_id}/output/final_subtitled.mp4"
            minio_client.upload_file(output_local, output_minio, content_type="video/mp4")
            
            return {
                "success": True,
                "video_path": output_minio,
                "presigned_url": minio_client.get_presigned_url(output_minio)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


video_renderer = VideoRenderer()
