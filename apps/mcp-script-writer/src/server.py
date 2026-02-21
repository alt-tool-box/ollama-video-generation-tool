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

from tools import enhance_prompt, generate_script, regenerate_scene

server = Server("mcp-script-writer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="enhance_prompt",
            description="Enhance a simple user prompt into a detailed creative brief for video creation",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "The user's simple video idea"
                    }
                },
                "required": ["user_prompt"]
            }
        ),
        Tool(
            name="generate_script",
            description="Generate a complete video script with scenes, image prompts, and narration",
            inputSchema={
                "type": "object",
                "properties": {
                    "enhanced_prompt": {
                        "type": "string",
                        "description": "The enhanced video concept"
                    },
                    "style": {
                        "type": "string",
                        "description": "Visual style for the video",
                        "default": "cinematic, 4k"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Target duration in seconds",
                        "default": 10
                    }
                },
                "required": ["enhanced_prompt"]
            }
        ),
        Tool(
            name="regenerate_scene",
            description="Regenerate a specific scene in the video script",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_id": {
                        "type": "integer",
                        "description": "The ID of the scene to regenerate"
                    },
                    "overall_concept": {
                        "type": "string",
                        "description": "The overall video concept"
                    },
                    "style": {
                        "type": "string",
                        "description": "Visual style for the video"
                    },
                    "previous_scene": {
                        "type": "object",
                        "description": "The previous scene data (optional)"
                    },
                    "next_scene": {
                        "type": "object",
                        "description": "The next scene data (optional)"
                    },
                    "user_feedback": {
                        "type": "string",
                        "description": "User feedback for regeneration (optional)"
                    }
                },
                "required": ["scene_id", "overall_concept", "style"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "enhance_prompt":
            result = enhance_prompt(arguments["user_prompt"])
        elif name == "generate_script":
            result = generate_script(
                arguments["enhanced_prompt"],
                arguments.get("style", "cinematic, 4k"),
                arguments.get("duration", 10)
            )
        elif name == "regenerate_scene":
            result = regenerate_scene(
                arguments["scene_id"],
                arguments["overall_concept"],
                arguments["style"],
                arguments.get("previous_scene"),
                arguments.get("next_scene"),
                arguments.get("user_feedback")
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
    port = int(os.getenv("PORT", "9001"))
    print(f"MCP Script Writer starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
