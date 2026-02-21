import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import ollama_client

SYSTEM_PROMPT = """You are a professional video script writer. Your job is to create detailed scene-by-scene scripts for video creation.

You must respond with a JSON object in this exact format:
```json
{
  "enhanced_prompt": "The overall video concept description",
  "scenes": [
    {
      "id": 1,
      "description": "What happens in this scene",
      "image_prompt": "Detailed prompt for AI image generation (include style, lighting, composition)",
      "duration_seconds": 3,
      "narration": "The voiceover text for this scene"
    }
  ],
  "total_duration": 10,
  "style": "cinematic, 4k"
}
```

Guidelines:
- Create 3-8 scenes depending on the content
- Each scene should be 2-5 seconds
- Image prompts should be detailed and specific for AI generation
- Narration should be concise and match the scene duration
- Include style keywords like: cinematic, 4k, detailed, professional lighting
- Ensure smooth visual flow between scenes"""


def generate_script(enhanced_prompt: str, style: str = "cinematic, 4k", duration: int = 10) -> dict:
    prompt = f"""Create a detailed video script for this concept:

Concept: "{enhanced_prompt}"
Style: {style}
Target Duration: {duration} seconds

Break it down into individual scenes with detailed image prompts and narration.
Remember to respond with valid JSON only."""

    response = ollama_client.generate(prompt, SYSTEM_PROMPT)
    return ollama_client.extract_json(response)
