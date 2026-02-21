import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..lib.minio_client import minio_client
from ..lib.logger import get_logger

from .job_service import JobService
from .websocket_manager import ws_manager
from ..mcp import mcp_manager

logger = get_logger("lead-app.workflow")


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = JobService(db)

    async def generate_script(self, job_id: UUID) -> dict:
        logger.info(f"[Job {job_id}] Starting script generation")

        job = await self.job_service.get_job(job_id)
        if not job:
            logger.error(f"[Job {job_id}] Job not found")
            return {"error": "Job not found"}

        logger.info(f"[Job {job_id}] Original prompt: {job.original_prompt[:100]}...")

        await self.job_service.update_job_status(job_id, "script_pending")
        await ws_manager.broadcast_status(str(job_id), "script_pending", "enhance_prompt", 0, "Enhancing prompt...")

        logger.info(f"[Job {job_id}] Calling MCP enhance_prompt...")
        enhanced = await mcp_manager.enhance_prompt(job.original_prompt)

        if "error" in enhanced:
            logger.error(f"[Job {job_id}] enhance_prompt failed: {enhanced['error']}")
            await self.job_service.update_job_status(job_id, "failed", enhanced["error"])
            return enhanced

        logger.info(f"[Job {job_id}] Prompt enhanced successfully")
        await ws_manager.broadcast_status(str(job_id), "script_pending", "generate_script", 50, "Generating script...")

        logger.info(f"[Job {job_id}] Calling MCP generate_script...")
        script_result = await mcp_manager.generate_script(
            enhanced.get("enhanced_prompt", job.original_prompt),
            enhanced.get("style", "cinematic, 4k"),
            enhanced.get("suggested_duration", 10)
        )

        if "error" in script_result:
            logger.error(f"[Job {job_id}] generate_script failed: {script_result['error']}")
            await self.job_service.update_job_status(job_id, "failed", script_result["error"])
            return script_result

        logger.info(f"[Job {job_id}] Script generated with {len(script_result.get('scenes', []))} scenes")

        await self.job_service.update_job_script(job_id, script_result)

        await self.job_service.create_script(
            job_id=job_id,
            enhanced_prompt=script_result.get("enhanced_prompt", ""),
            scenes=script_result.get("scenes", []),
            total_duration=script_result.get("total_duration", 0),
            style=script_result.get("style", "cinematic")
        )

        await self.job_service.update_job_status(job_id, "script_ready")
        await ws_manager.broadcast_status(str(job_id), "script_ready", "generate_script", 100, "Script ready for review")

        logger.info(f"[Job {job_id}] Script generation completed successfully")
        return script_result

    async def regenerate_scene(self, job_id: UUID, scene_id: int, user_feedback: str = None) -> dict:
        job = await self.job_service.get_job(job_id)
        if not job or not job.enhanced_script:
            return {"error": "Job or script not found"}

        scenes = job.enhanced_script.get("scenes", [])
        style = job.enhanced_script.get("style", "cinematic")
        enhanced_prompt = job.enhanced_script.get("enhanced_prompt", "")

        prev_scene = None
        next_scene = None

        for i, scene in enumerate(scenes):
            if scene["id"] == scene_id:
                if i > 0:
                    prev_scene = scenes[i - 1]
                if i < len(scenes) - 1:
                    next_scene = scenes[i + 1]
                break

        new_scene = await mcp_manager.regenerate_scene(
            scene_id=scene_id,
            overall_concept=enhanced_prompt,
            style=style,
            previous_scene=prev_scene,
            next_scene=next_scene,
            user_feedback=user_feedback
        )

        if "error" in new_scene:
            return new_scene

        for i, scene in enumerate(scenes):
            if scene["id"] == scene_id:
                scenes[i] = new_scene
                break

        updated_script = job.enhanced_script.copy()
        updated_script["scenes"] = scenes

        await self.job_service.update_job_script(job_id, updated_script)

        return new_scene

    async def approve_and_generate(self, job_id: UUID) -> dict:
        logger.info(f"[Job {job_id}] Starting approve and generate workflow")

        job = await self.job_service.get_job(job_id)
        if not job:
            logger.error(f"[Job {job_id}] Job not found")
            return {"error": "Job not found"}

        if not job.enhanced_script:
            logger.error(f"[Job {job_id}] No script to approve")
            return {"error": "No script to approve"}

        logger.info(f"[Job {job_id}] Script approved, starting video generation")
        await self.job_service.update_job_status(job_id, "approved")
        await ws_manager.broadcast_status(str(job_id), "approved", None, 0, "Script approved, starting generation...")

        await self.job_service.update_job_status(job_id, "processing")

        try:
            result = await self._execute_generation(job_id, job.enhanced_script)
            return result
        except Exception as e:
            logger.error(f"[Job {job_id}] Generation failed with exception: {str(e)}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            await ws_manager.broadcast_status(str(job_id), "failed", None, 0, None, str(e))
            return {"error": str(e)}

    async def _execute_generation(self, job_id: UUID, script: dict) -> dict:
        job_id_str = str(job_id)
        scenes = script.get("scenes", [])
        style = script.get("style", "cinematic")

        logger.info(f"[Job {job_id}] Executing generation for {len(scenes)} scenes")

        clip_step = await self.job_service.create_job_step(job_id, "clip_generation")
        tts_step = await self.job_service.create_job_step(job_id, "tts_generation")
        video_step = await self.job_service.create_job_step(job_id, "video_rendering")

        # Step 1: AnimateDiff Video Clip Generation
        logger.info(f"[Job {job_id}] Step 1/3: Starting AnimateDiff clip generation...")
        await self.job_service.update_job_step(clip_step.id, "in_progress", 0)
        await ws_manager.broadcast_status(job_id_str, "processing", "clip_generation", 0, "Generating motion clips (AnimateDiff)...")

        logger.info(f"[Job {job_id}] Calling MCP generate_frames for {len(scenes)} scenes")
        clip_result = await mcp_manager.generate_frames(
            scenes=[{"id": s["id"], "image_prompt": s["image_prompt"], "duration_seconds": s["duration_seconds"]} for s in scenes],
            job_id=job_id_str,
            style=style
        )

        if not clip_result.get("success") and clip_result.get("completed", 0) == 0:
            error_msg = clip_result.get("error")
            if not error_msg:
                clip_errors = [c.get("error", "Unknown") for c in clip_result.get("clips", []) if not c.get("success")]
                error_msg = "; ".join(clip_errors[:3]) if clip_errors else "All clips failed to generate"
            logger.error(f"[Job {job_id}] Clip generation failed: {error_msg}")
            await self.job_service.update_job_step(clip_step.id, "failed", error_message=error_msg)
            return {"error": f"Clip generation failed: {error_msg}"}

        if not clip_result.get("success"):
            failed_clips = [c for c in clip_result.get("clips", []) if not c.get("success")]
            logger.warning(f"[Job {job_id}] {len(failed_clips)} clips failed, continuing with {clip_result.get('completed', 0)} successful")

        logger.info(f"[Job {job_id}] Clip generation completed: {clip_result.get('completed', 0)}/{clip_result.get('total', 0)} clips")
        await self.job_service.update_job_step(clip_step.id, "completed", 100)

        for clip in clip_result.get("clips", []):
            if clip.get("success"):
                await self.job_service.create_asset(
                    job_id, "clip", clip["clip_path"],
                    {"scene_id": clip["scene_id"], "clip_duration": clip.get("clip_duration")}
                )

        await ws_manager.broadcast_status(job_id_str, "processing", "clip_generation", 100, "Motion clips generated")

        # Step 2: TTS Generation
        logger.info(f"[Job {job_id}] Step 2/3: Starting TTS generation...")
        await self.job_service.update_job_step(tts_step.id, "in_progress", 0)
        await ws_manager.broadcast_status(job_id_str, "processing", "tts_generation", 0, "Generating audio...")

        tts_scenes = [{"id": s["id"], "narration": s.get("narration", "")} for s in scenes]
        narration_count = len([s for s in tts_scenes if s.get("narration")])
        logger.info(f"[Job {job_id}] Calling MCP text_to_speech_batch for {len(scenes)} scenes ({narration_count} with narration)")
        tts_result = await mcp_manager.text_to_speech_batch(
            scenes=tts_scenes,
            job_id=job_id_str
        )
        logger.debug(f"[Job {job_id}] TTS result: {tts_result}")

        tts_completed = tts_result.get("completed", 0)
        tts_total = tts_result.get("total", 0)
        if tts_completed == 0 and tts_total > 0 and tts_result.get("error"):
            logger.error(f"[Job {job_id}] TTS generation completely failed: {tts_result.get('error')}")
            await self.job_service.update_job_step(tts_step.id, "failed", error_message=tts_result.get("error"))
            return {"error": f"TTS generation failed: {tts_result.get('error')}"}

        if not tts_result.get("success"):
            failed_count = tts_result.get("failed", 0)
            tts_errors = tts_result.get("errors", [])
            logger.warning(f"[Job {job_id}] TTS had {failed_count} failures, but continuing with {tts_completed} successful")
            if tts_errors:
                for err in tts_errors:
                    logger.warning(f"[Job {job_id}] TTS error: {err}")

        logger.info(f"[Job {job_id}] TTS generation completed: {tts_result.get('completed', 0)}/{tts_result.get('total', 0)} audio segments")
        await self.job_service.update_job_step(tts_step.id, "completed", 100)

        for audio in tts_result.get("audio_segments", []):
            if audio.get("success") and audio.get("audio_path"):
                await self.job_service.create_asset(job_id, "audio", audio["audio_path"], {"scene_id": audio["scene_id"]})

        await ws_manager.broadcast_status(job_id_str, "processing", "tts_generation", 100, "Audio generated")

        # Step 3: Video Rendering
        logger.info(f"[Job {job_id}] Step 3/3: Starting video rendering...")
        await self.job_service.update_job_step(video_step.id, "in_progress", 0)
        await ws_manager.broadcast_status(job_id_str, "processing", "video_rendering", 0, "Rendering final video...")

        frames_for_render = []
        audio_segments = {a["scene_id"]: a for a in tts_result.get("audio_segments", []) if a.get("success")}

        for clip in clip_result.get("clips", []):
            if clip.get("success"):
                scene = next((s for s in scenes if s["id"] == clip["scene_id"]), None)
                frame_data = {
                    "clip_path": clip["clip_path"],
                    "duration": scene["duration_seconds"] if scene else 3
                }

                if clip["scene_id"] in audio_segments and audio_segments[clip["scene_id"]].get("audio_path"):
                    frame_data["audio_path"] = audio_segments[clip["scene_id"]]["audio_path"]

                frames_for_render.append(frame_data)

        logger.info(f"[Job {job_id}] Calling MCP render_video with {len(frames_for_render)} clips")
        video_result = await mcp_manager.render_video(
            job_id=job_id_str,
            frames=frames_for_render,
            add_transitions=True
        )

        if not video_result.get("success"):
            logger.error(f"[Job {job_id}] Video rendering failed: {video_result.get('error')}")
            await self.job_service.update_job_step(video_step.id, "failed", error_message=video_result.get("error"))
            return {"error": f"Video rendering failed: {video_result.get('error')}"}

        logger.info(f"[Job {job_id}] Video rendering completed: {video_result.get('video_path')}")
        await self.job_service.update_job_step(video_step.id, "completed", 100, video_result.get("video_path"))
        await self.job_service.create_asset(job_id, "video", video_result["video_path"], {"duration": video_result.get("duration")})
        await self.job_service.update_job_output(job_id, video_result["video_path"])

        await self.job_service.update_job_status(job_id, "completed")
        await ws_manager.broadcast_status(job_id_str, "completed", "video_rendering", 100, "Video ready!")

        logger.info(f"[Job {job_id}] Video generation completed successfully!")
        return {
            "success": True,
            "video_path": video_result["video_path"],
            "presigned_url": video_result.get("presigned_url")
        }

    async def retry_job(self, job_id: UUID) -> dict:
        """Retry a stuck or failed job from its last successful step."""
        logger.info(f"[Job {job_id}] Starting retry workflow")

        job = await self.job_service.get_job(job_id)
        if not job:
            logger.error(f"[Job {job_id}] Job not found for retry")
            return {"error": "Job not found"}

        current_status = job.status
        logger.info(f"[Job {job_id}] Current status: {current_status}")

        if current_status == "script_pending":
            logger.info(f"[Job {job_id}] Retrying script generation")
            return await self.generate_script(job_id)
        elif current_status in ["approved", "processing", "failed"]:
            return await self._retry_generation(job_id, job)
        elif current_status == "draft":
            logger.info(f"[Job {job_id}] Starting script generation for draft job")
            return await self.generate_script(job_id)
        elif current_status == "script_ready":
            logger.info(f"[Job {job_id}] Script ready, starting generation")
            return await self.approve_and_generate(job_id)
        elif current_status == "completed":
            logger.info(f"[Job {job_id}] Job already completed, nothing to retry")
            return {"success": True, "message": "Job already completed"}
        else:
            logger.error(f"[Job {job_id}] Unknown status for retry: {current_status}")
            return {"error": f"Cannot retry job in status: {current_status}"}

    async def _retry_generation(self, job_id: UUID, job) -> dict:
        """Retry generation from the last failed step."""
        job_id_str = str(job_id)

        if not job.enhanced_script:
            logger.error(f"[Job {job_id}] No script found, need to regenerate")
            await self.job_service.update_job_status(job_id, "draft")
            return await self.generate_script(job_id)

        script = job.enhanced_script
        scenes = script.get("scenes", [])
        style = script.get("style", "cinematic")

        steps = {step.step_name: step for step in job.steps}
        clip_step = steps.get("clip_generation") or steps.get("image_generation")
        tts_step = steps.get("tts_generation")
        video_step = steps.get("video_rendering")

        has_clips = clip_step and clip_step.status == "completed"
        has_audio = tts_step and tts_step.status == "completed"

        logger.info(f"[Job {job_id}] Step status - Clips: {has_clips}, Audio: {has_audio}")

        await self.job_service.update_job_status(job_id, "processing")
        await ws_manager.broadcast_status(job_id_str, "processing", None, 0, "Resuming generation...")

        try:
            clip_result = None
            tts_result = None

            if has_clips:
                logger.info(f"[Job {job_id}] Using existing clips")
                clips = []
                for asset in job.assets:
                    if asset.asset_type in ("clip", "frame"):
                        clips.append({
                            "scene_id": asset.asset_metadata.get("scene_id"),
                            "success": True,
                            "clip_path": asset.minio_path,
                            "clip_duration": asset.asset_metadata.get("clip_duration")
                        })
                clip_result = {"success": True, "clips": clips}
            else:
                logger.info(f"[Job {job_id}] Generating motion clips...")
                if not clip_step:
                    clip_step = await self.job_service.create_job_step(job_id, "clip_generation")
                await self.job_service.update_job_step(clip_step.id, "in_progress", 0)
                await ws_manager.broadcast_status(job_id_str, "processing", "clip_generation", 0, "Generating motion clips (AnimateDiff)...")

                clip_result = await mcp_manager.generate_frames(
                    scenes=[{"id": s["id"], "image_prompt": s["image_prompt"], "duration_seconds": s["duration_seconds"]} for s in scenes],
                    job_id=job_id_str,
                    style=style
                )

                if not clip_result.get("success") and clip_result.get("completed", 0) == 0:
                    error_msg = clip_result.get("error")
                    if not error_msg:
                        clip_errors = [c.get("error", "Unknown") for c in clip_result.get("clips", []) if not c.get("success")]
                        error_msg = "; ".join(clip_errors[:3]) if clip_errors else "All clips failed to generate"
                    logger.error(f"[Job {job_id}] Clip generation failed: {error_msg}")
                    await self.job_service.update_job_step(clip_step.id, "failed", error_message=error_msg)
                    await self.job_service.update_job_status(job_id, "failed", f"Clip generation failed: {error_msg}")
                    return {"error": f"Clip generation failed: {error_msg}"}

                await self.job_service.update_job_step(clip_step.id, "completed", 100)
                for clip in clip_result.get("clips", []):
                    if clip.get("success"):
                        await self.job_service.create_asset(
                            job_id, "clip", clip["clip_path"],
                            {"scene_id": clip["scene_id"], "clip_duration": clip.get("clip_duration")}
                        )

                await ws_manager.broadcast_status(job_id_str, "processing", "clip_generation", 100, "Motion clips generated")

            if has_audio:
                logger.info(f"[Job {job_id}] Using existing audio")
                audio_segments = []
                for asset in job.assets:
                    if asset.asset_type == "audio":
                        audio_segments.append({
                            "scene_id": asset.asset_metadata.get("scene_id"),
                            "success": True,
                            "audio_path": asset.minio_path
                        })
                tts_result = {"success": True, "audio_segments": audio_segments}
            else:
                logger.info(f"[Job {job_id}] Generating audio...")
                if not tts_step:
                    tts_step = await self.job_service.create_job_step(job_id, "tts_generation")
                await self.job_service.update_job_step(tts_step.id, "in_progress", 0)
                await ws_manager.broadcast_status(job_id_str, "processing", "tts_generation", 0, "Generating audio...")

                tts_result = await mcp_manager.text_to_speech_batch(
                    scenes=[{"id": s["id"], "narration": s.get("narration", "")} for s in scenes],
                    job_id=job_id_str
                )

                tts_completed = tts_result.get("completed", 0)
                tts_total = tts_result.get("total", 0)
                if tts_completed == 0 and tts_total > 0 and tts_result.get("error"):
                    logger.error(f"[Job {job_id}] TTS generation completely failed: {tts_result.get('error')}")
                    await self.job_service.update_job_step(tts_step.id, "failed", error_message=tts_result.get("error"))
                    await self.job_service.update_job_status(job_id, "failed", f"TTS generation failed: {tts_result.get('error')}")
                    return {"error": f"TTS generation failed: {tts_result.get('error')}"}

                if not tts_result.get("success"):
                    failed_count = tts_result.get("failed", 0)
                    logger.warning(f"[Job {job_id}] TTS had {failed_count} failures, but continuing with {tts_completed} successful")

                await self.job_service.update_job_step(tts_step.id, "completed", 100)
                for audio in tts_result.get("audio_segments", []):
                    if audio.get("success") and audio.get("audio_path"):
                        await self.job_service.create_asset(job_id, "audio", audio["audio_path"], {"scene_id": audio["scene_id"]})

                await ws_manager.broadcast_status(job_id_str, "processing", "tts_generation", 100, "Audio generated")

            logger.info(f"[Job {job_id}] Rendering video...")
            if not video_step:
                video_step = await self.job_service.create_job_step(job_id, "video_rendering")
            await self.job_service.update_job_step(video_step.id, "in_progress", 0)
            await ws_manager.broadcast_status(job_id_str, "processing", "video_rendering", 0, "Rendering final video...")

            frames_for_render = []
            audio_segments = {a["scene_id"]: a for a in tts_result.get("audio_segments", []) if a.get("success")}

            for clip in clip_result.get("clips", []):
                if clip.get("success"):
                    scene = next((s for s in scenes if s["id"] == clip["scene_id"]), None)
                    frame_data = {
                        "clip_path": clip["clip_path"],
                        "duration": scene["duration_seconds"] if scene else 3
                    }

                    if clip["scene_id"] in audio_segments and audio_segments[clip["scene_id"]].get("audio_path"):
                        frame_data["audio_path"] = audio_segments[clip["scene_id"]]["audio_path"]

                    frames_for_render.append(frame_data)

            video_result = await mcp_manager.render_video(
                job_id=job_id_str,
                frames=frames_for_render,
                add_transitions=True
            )

            if not video_result.get("success"):
                logger.error(f"[Job {job_id}] Video rendering failed: {video_result.get('error')}")
                await self.job_service.update_job_step(video_step.id, "failed", error_message=video_result.get("error"))
                await self.job_service.update_job_status(job_id, "failed", f"Video rendering failed: {video_result.get('error')}")
                return {"error": f"Video rendering failed: {video_result.get('error')}"}

            logger.info(f"[Job {job_id}] Video rendering completed")
            await self.job_service.update_job_step(video_step.id, "completed", 100, video_result.get("video_path"))
            await self.job_service.create_asset(job_id, "video", video_result["video_path"], {"duration": video_result.get("duration")})
            await self.job_service.update_job_output(job_id, video_result["video_path"])

            await self.job_service.update_job_status(job_id, "completed")
            await ws_manager.broadcast_status(job_id_str, "completed", "video_rendering", 100, "Video ready!")

            logger.info(f"[Job {job_id}] Retry completed successfully!")
            return {"success": True, "video_path": video_result["video_path"]}

        except Exception as e:
            logger.error(f"[Job {job_id}] Retry failed with exception: {str(e)}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            await ws_manager.broadcast_status(job_id_str, "failed", None, 0, None, str(e))
            return {"error": str(e)}
