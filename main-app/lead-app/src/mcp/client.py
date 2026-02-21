import json
import time
import traceback
from mcp import ClientSession
from mcp.client.sse import sse_client

from ..lib.logger import get_logger
from ..lib.config import config

logger = get_logger("lead-app.mcp")


class MCPClientManager:
    def _get_server_url(self, server_name: str) -> str:
        """Returns the HTTP SSE URL for each MCP server."""
        urls = {
            "script_writer": config.MCP_SCRIPT_WRITER_URL,
            "image_gen": config.MCP_IMAGE_GEN_URL,
            "tts": config.MCP_TTS_URL,
            "video_gen": config.MCP_VIDEO_GEN_URL,
        }
        return urls.get(server_name)

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        url = self._get_server_url(server_name)

        if not url:
            logger.error(f"Unknown MCP server: {server_name}")
            return {"error": f"Unknown server: {server_name}"}

        logger.info(f"MCP call: {server_name}.{tool_name}() -> {url}")
        start_time = time.time()

        try:
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.debug(f"MCP session initialized for {server_name}")

                    result = await session.call_tool(tool_name, arguments)

                    elapsed = time.time() - start_time

                    if result.content and len(result.content) > 0:
                        text_content = result.content[0]
                        if hasattr(text_content, 'text'):
                            parsed = json.loads(text_content.text)
                            if "error" in parsed:
                                logger.error(f"MCP {server_name}.{tool_name} returned error: {parsed['error']} ({elapsed:.2f}s)")
                            else:
                                logger.info(f"MCP {server_name}.{tool_name} completed successfully ({elapsed:.2f}s)")
                            return parsed

                    logger.warning(f"MCP {server_name}.{tool_name} returned no response ({elapsed:.2f}s)")
                    return {"error": "No response from MCP server"}
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"MCP {server_name}.{tool_name} failed ({elapsed:.2f}s): {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {"error": str(e)}

    async def enhance_prompt(self, user_prompt: str) -> dict:
        return await self.call_tool("script_writer", "enhance_prompt", {"user_prompt": user_prompt})

    async def generate_script(self, enhanced_prompt: str, style: str = "cinematic, 4k", duration: int = 10) -> dict:
        return await self.call_tool("script_writer", "generate_script", {
            "enhanced_prompt": enhanced_prompt,
            "style": style,
            "duration": duration
        })

    async def regenerate_scene(self, scene_id: int, overall_concept: str, style: str,
                                previous_scene: dict = None, next_scene: dict = None,
                                user_feedback: str = None) -> dict:
        args = {
            "scene_id": scene_id,
            "overall_concept": overall_concept,
            "style": style
        }
        if previous_scene:
            args["previous_scene"] = previous_scene
        if next_scene:
            args["next_scene"] = next_scene
        if user_feedback:
            args["user_feedback"] = user_feedback

        return await self.call_tool("script_writer", "regenerate_scene", args)

    async def generate_image(self, prompt: str, job_id: str, scene_id: int,
                             width: int = 1024, height: int = 576, style: str = "cinematic") -> dict:
        return await self.call_tool("image_gen", "generate_image", {
            "prompt": prompt,
            "job_id": job_id,
            "scene_id": scene_id,
            "width": width,
            "height": height,
            "style": style
        })

    async def generate_frames(self, scenes: list, job_id: str,
                              width: int = 512, height: int = 512, style: str = "cinematic",
                              num_frames: int = 16, fps: int = 8) -> dict:
        return await self.call_tool("image_gen", "generate_frames", {
            "scenes": scenes,
            "job_id": job_id,
            "width": width,
            "height": height,
            "style": style,
            "num_frames": num_frames,
            "fps": fps
        })

    async def text_to_speech(self, text: str, job_id: str, scene_id: int,
                             voice: str = "default", language: str = "en") -> dict:
        return await self.call_tool("tts", "text_to_speech", {
            "text": text,
            "job_id": job_id,
            "scene_id": scene_id,
            "voice": voice,
            "language": language
        })

    async def text_to_speech_batch(self, scenes: list, job_id: str,
                                   voice: str = "default", language: str = "en") -> dict:
        return await self.call_tool("tts", "text_to_speech_batch", {
            "scenes": scenes,
            "job_id": job_id,
            "voice": voice,
            "language": language
        })

    async def list_voices(self) -> dict:
        return await self.call_tool("tts", "list_voices", {})

    async def render_video(self, job_id: str, frames: list, audio_path: str = None,
                          fps: int = 24, add_transitions: bool = True) -> dict:
        args = {
            "job_id": job_id,
            "frames": frames,
            "fps": fps,
            "add_transitions": add_transitions
        }
        if audio_path:
            args["audio_path"] = audio_path

        return await self.call_tool("video_gen", "render_video", args)

    async def add_subtitles(self, job_id: str, video_path: str, subtitles: list) -> dict:
        return await self.call_tool("video_gen", "add_subtitles", {
            "job_id": job_id,
            "video_path": video_path,
            "subtitles": subtitles
        })


mcp_manager = MCPClientManager()
