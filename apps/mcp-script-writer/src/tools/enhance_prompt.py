import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import ollama_client

SYSTEM_PROMPT = """You are a creative video script writer. Your job is to take a simple user prompt and enhance it into a detailed, vivid description for video creation.

You must respond with a JSON object in this exact format:
```json
{
  "enhanced_prompt": "A detailed, vivid description of the video concept",
  "style": "cinematic, 4k, detailed",
  "mood": "The overall mood/tone of the video",
  "suggested_duration": 10
}
```

Guidelines:
- Expand vague ideas into specific, visual descriptions
- Add sensory details (colors, textures, lighting)
- Suggest a visual style
- Keep it achievable with AI image generation
- Suggested duration should be between 5-60 seconds"""


def enhance_prompt(user_prompt: str) -> dict:
    prompt = f"""Enhance this video idea into a detailed creative brief:

User's idea: "{user_prompt}"

Remember to respond with valid JSON only."""

    response = ollama_client.generate(prompt, SYSTEM_PROMPT)
    return ollama_client.extract_json(response)
