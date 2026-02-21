import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from client import ollama_client, OllamaClient

__all__ = ["ollama_client", "OllamaClient"]
