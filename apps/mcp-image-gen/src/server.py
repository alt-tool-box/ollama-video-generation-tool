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

from tools import generate_image, generate_video_clip, generate_frames

server = Server("mcp-image-gen")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_image",
            description="Generate a single static image from a prompt using ComfyUI/Stable Diffusion (SDXL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The image generation prompt"},
                    "job_id": {"type": "string", "description": "The job ID for file organization"},
                    "scene_id": {"type": "integer", "description": "The scene ID"},
                    "width": {"type": "integer", "description": "Image width", "default": 1024},
                    "height": {"type": "integer", "description": "Image height", "default": 576},
                    "style": {"type": "string", "description": "Style keywords", "default": "cinematic"}
                },
                "required": ["prompt", "job_id", "scene_id"]
            }
        ),
        Tool(
            name="generate_video_clip",
            description="Generate a single animated video clip using AnimateDiff for motion video",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The video generation prompt"},
                    "job_id": {"type": "string", "description": "The job ID for file organization"},
                    "scene_id": {"type": "integer", "description": "The scene ID"},
                    "width": {"type": "integer", "description": "Video width (512 recommended)", "default": 512},
                    "height": {"type": "integer", "description": "Video height (512 recommended)", "default": 512},
                    "style": {"type": "string", "description": "Style keywords", "default": "cinematic"},
                    "num_frames": {"type": "integer", "description": "Number of frames (16 recommended)", "default": 16},
                    "fps": {"type": "integer", "description": "Frames per second", "default": 8}
                },
                "required": ["prompt", "job_id", "scene_id"]
            }
        ),
        Tool(
            name="generate_frames",
            description="Generate animated video clips for multiple scenes using AnimateDiff (motion video)",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "Array of scene objects with id, image_prompt, duration_seconds",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "image_prompt": {"type": "string"},
                                "duration_seconds": {"type": "number"}
                            }
                        }
                    },
                    "job_id": {"type": "string", "description": "The job ID for file organization"},
                    "width": {"type": "integer", "description": "Video width (512 recommended)", "default": 512},
                    "height": {"type": "integer", "description": "Video height (512 recommended)", "default": 512},
                    "style": {"type": "string", "description": "Style keywords", "default": "cinematic"},
                    "num_frames": {"type": "integer", "description": "Frames per clip (16 recommended)", "default": 16},
                    "fps": {"type": "integer", "description": "Frames per second", "default": 8}
                },
                "required": ["scenes", "job_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "generate_image":
            result = await generate_image(
                arguments["prompt"], arguments["job_id"], arguments["scene_id"],
                arguments.get("width", 1024), arguments.get("height", 576),
                arguments.get("style", "cinematic")
            )
        elif name == "generate_video_clip":
            result = await generate_video_clip(
                arguments["prompt"], arguments["job_id"], arguments["scene_id"],
                arguments.get("width", 512), arguments.get("height", 512),
                arguments.get("style", "cinematic"),
                arguments.get("num_frames", 16), arguments.get("fps", 8)
            )
        elif name == "generate_frames":
            result = await generate_frames(
                arguments["scenes"], arguments["job_id"],
                arguments.get("width", 512), arguments.get("height", 512),
                arguments.get("style", "cinematic"),
                arguments.get("num_frames", 16), arguments.get("fps", 8)
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
    port = int(os.getenv("PORT", "9002"))
    print(f"MCP Image Gen starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
