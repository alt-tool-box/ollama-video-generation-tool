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

from tools import text_to_speech, list_voices
from tools.text_to_speech import text_to_speech_batch

server = Server("mcp-tts")


@server.list_tools()
async def list_tools_handler() -> list[Tool]:
    return [
        Tool(
            name="text_to_speech",
            description="Convert text to speech audio",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to convert to speech"},
                    "job_id": {"type": "string", "description": "The job ID for file organization"},
                    "scene_id": {"type": "integer", "description": "The scene ID"},
                    "voice": {"type": "string", "description": "Voice to use", "default": "default"},
                    "language": {"type": "string", "description": "Language code", "default": "en"}
                },
                "required": ["text", "job_id", "scene_id"]
            }
        ),
        Tool(
            name="text_to_speech_batch",
            description="Convert multiple scenes to speech audio",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "Array of scene objects with id and narration",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "narration": {"type": "string"}
                            }
                        }
                    },
                    "job_id": {"type": "string", "description": "The job ID for file organization"},
                    "voice": {"type": "string", "description": "Voice to use", "default": "default"},
                    "language": {"type": "string", "description": "Language code", "default": "en"}
                },
                "required": ["scenes", "job_id"]
            }
        ),
        Tool(
            name="list_voices",
            description="List available TTS voices",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "text_to_speech":
            result = text_to_speech(
                arguments["text"], arguments["job_id"], arguments["scene_id"],
                arguments.get("voice", "default"), arguments.get("language", "en")
            )
        elif name == "text_to_speech_batch":
            result = text_to_speech_batch(
                arguments["scenes"], arguments["job_id"],
                arguments.get("voice", "default"), arguments.get("language", "en")
            )
        elif name == "list_voices":
            result = list_voices()
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
    port = int(os.getenv("PORT", "9003"))
    print(f"MCP TTS starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
