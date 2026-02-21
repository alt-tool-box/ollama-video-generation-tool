import asyncio
import json
import os
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route
import uvicorn

from tools import render_video, add_subtitles

server = Server("mcp-video-gen")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="render_video",
            description="Render final video from video clips (AnimateDiff) or static images with audio",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The job ID"},
                    "frames": {
                        "type": "array",
                        "description": "Array of frame/clip objects with clip_path or image_path, duration, optional audio_path",
                        "items": {
                            "type": "object",
                            "properties": {
                                "clip_path": {"type": "string", "description": "MinIO path to video clip"},
                                "image_path": {"type": "string", "description": "MinIO path to static image (fallback)"},
                                "duration": {"type": "number"},
                                "audio_path": {"type": "string"}
                            },
                            "required": ["duration"]
                        }
                    },
                    "audio_path": {"type": "string", "description": "Path to full audio track (optional)"},
                    "fps": {"type": "integer", "description": "Frames per second", "default": 24},
                    "add_transitions": {"type": "boolean", "description": "Add fade transitions", "default": True},
                    "transition_duration": {"type": "number", "description": "Transition duration in seconds", "default": 0.5}
                },
                "required": ["job_id", "frames"]
            }
        ),
        Tool(
            name="add_subtitles",
            description="Add subtitles to a video",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The job ID"},
                    "video_path": {"type": "string", "description": "MinIO path to the video"},
                    "subtitles": {
                        "type": "array",
                        "description": "Array of subtitle objects",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "start": {"type": "number"},
                                "duration": {"type": "number"}
                            },
                            "required": ["text", "start", "duration"]
                        }
                    },
                    "font_size": {"type": "integer", "description": "Font size", "default": 36},
                    "font_color": {"type": "string", "description": "Font color", "default": "white"},
                    "bg_color": {"type": "string", "description": "Background color", "default": "black"}
                },
                "required": ["job_id", "video_path", "subtitles"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "render_video":
            result = render_video(
                job_id=arguments["job_id"],
                frames=arguments["frames"],
                audio_path=arguments.get("audio_path"),
                fps=arguments.get("fps", 24),
                add_transitions=arguments.get("add_transitions", True),
                transition_duration=arguments.get("transition_duration", 0.5)
            )
        elif name == "add_subtitles":
            result = add_subtitles(
                job_id=arguments["job_id"],
                video_path=arguments["video_path"],
                subtitles=arguments["subtitles"],
                font_size=arguments.get("font_size", 36),
                font_color=arguments.get("font_color", "white"),
                bg_color=arguments.get("bg_color", "black")
            )
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        return [TextContent(type="text", text=json.dumps(result))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


sse = SseServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())
    return Response()


app = Starlette(
    debug=False,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "9004"))
    print(f"MCP Video Gen starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
