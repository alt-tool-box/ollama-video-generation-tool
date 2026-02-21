import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from text_to_speech import text_to_speech
from list_voices import list_voices

__all__ = ["text_to_speech", "list_voices"]
