import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import ollama_client

SYSTEM_PROMPT = """You are a professional video script writer. Your job is to regenerate a specific scene in a video script.

You must respond with a JSON object for a single scene in this exact format:
```json
{
  "id": 1,
  "description": "What happens in this scene",
  "image_prompt": "Detailed prompt for AI image generation",
  "duration_seconds": 3,
  "narration": "The voiceover text for this scene"
}
```

Guidelines:
- Keep the scene consistent with the overall video style
- Make the image prompt detailed and specific
- Ensure narration matches the duration
- Maintain continuity with surrounding scenes"""


def regenerate_scene(
    scene_id: int,
    overall_concept: str,
    style: str,
    previous_scene: dict = None,
    next_scene: dict = None,
    user_feedback: str = None
) -> dict:
    context = f"""Video concept: "{overall_concept}"
Style: {style}
Scene ID: {scene_id}"""

    if previous_scene:
        context += f"\nPrevious scene: {previous_scene.get('description', 'N/A')}"
    
    if next_scene:
        context += f"\nNext scene: {next_scene.get('description', 'N/A')}"
    
    if user_feedback:
        context += f"\nUser feedback: {user_feedback}"

    prompt = f"""{context}

Regenerate scene {scene_id} based on the context above.
Remember to respond with valid JSON only."""

    response = ollama_client.generate(prompt, SYSTEM_PROMPT)
    return ollama_client.extract_json(response)
