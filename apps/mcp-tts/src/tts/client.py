import os
import sys
import tempfile
import io
import warnings
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))
from config import config

# Auto-agree to Coqui TTS license to prevent stdout prompts
os.environ["COQUI_TOS_AGREED"] = "1"

# Fix for PyTorch 2.6+ weights_only default change
# Monkey-patch torch.load to use weights_only=False for TTS model loading
import torch
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    # Force weights_only=False for Coqui TTS compatibility
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load


class TTSClient:
    def __init__(self):
        self.model_name = config.TTS_MODEL
        self._tts = None
        self._resolved_speaker = None
    
    @property
    def tts(self):
        if self._tts is None:
            # Suppress stdout/stderr during TTS initialization to prevent 
            # license prompts from breaking MCP JSON communication
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                from TTS.api import TTS
                self._tts = TTS(model_name=self.model_name, progress_bar=False)
            # Resolve a valid speaker once at init time
            self._resolved_speaker = self._find_speaker()
        return self._tts
    
    def _find_speaker(self) -> str:
        """Find a valid speaker name from the loaded model.
        
        Tries multiple approaches since Coqui TTS versions store 
        speaker info in different places.
        """
        tts = self._tts
        if tts is None:
            return None
        
        # Approach 1: tts.speakers (list of speaker names)
        try:
            speakers = getattr(tts, 'speakers', None)
            if speakers and len(speakers) > 0:
                if isinstance(speakers, (list, tuple)):
                    return speakers[0]
                # Could be dict_keys or other iterable
                return next(iter(speakers))
        except Exception:
            pass
        
        # Approach 2: synthesizer -> tts_model -> speaker_manager
        try:
            synth = getattr(tts, 'synthesizer', None)
            if synth:
                model = getattr(synth, 'tts_model', None)
                if model:
                    sm = getattr(model, 'speaker_manager', None)
                    if sm:
                        name_to_id = getattr(sm, 'name_to_id', None)
                        if name_to_id:
                            if isinstance(name_to_id, dict):
                                keys = list(name_to_id.keys())
                            else:
                                keys = list(name_to_id)
                            if keys:
                                return keys[0]
        except Exception:
            pass
        
        # Approach 3: synthesizer -> tts_config -> speakers
        try:
            synth = getattr(tts, 'synthesizer', None)
            if synth:
                tts_config = getattr(synth, 'tts_config', None)
                if tts_config:
                    speakers = getattr(tts_config, 'speakers', None)
                    if speakers:
                        if isinstance(speakers, dict):
                            return list(speakers.keys())[0]
                        elif isinstance(speakers, (list, tuple)) and len(speakers) > 0:
                            return speakers[0]
                        else:
                            return next(iter(speakers))
        except Exception:
            pass
        
        return None
    
    def list_voices(self) -> list:
        # Force model load
        _ = self.tts
        if self._resolved_speaker:
            return [self._resolved_speaker]
        return ["default"]
    
    def synthesize(self, text: str, output_path: str, voice: str = "default", language: str = "en") -> dict:
        try:
            is_xtts = "xtts" in self.model_name.lower()
            
            # Build kwargs for tts_to_file
            kwargs = {"text": text, "file_path": output_path}
            
            # Add speaker if model needs one
            speaker = self._resolved_speaker
            if voice != "default":
                speaker = voice
            
            if speaker:
                kwargs["speaker"] = speaker
            
            # Add language for multilingual/XTTS models
            if is_xtts or getattr(self.tts, 'is_multi_lingual', False):
                kwargs["language"] = language
            
            self.tts.tts_to_file(**kwargs)
            
            import wave
            with wave.open(output_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
            
            return {
                "success": True,
                "output_path": output_path,
                "duration": duration
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def synthesize_to_bytes(self, text: str, voice: str = "default", language: str = "en") -> tuple:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            result = self.synthesize(text, temp_path, voice, language)
            if not result["success"]:
                return None, 0, result["error"]
            
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data, result["duration"], None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


tts_client = TTSClient()
