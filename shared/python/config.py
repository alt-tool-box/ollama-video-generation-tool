import os
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"

if not env_path.exists():
    env_example = root_dir / ".env.example"
    if env_example.exists():
        import shutil
        shutil.copy(env_example, env_path)

load_dotenv(env_path)


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/video_creation")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "video-creation")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
    
    COMFYUI_URL: str = os.getenv("COMFYUI_URL", "http://localhost:8188")
    
    TTS_MODEL: str = os.getenv("TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    
    LEAD_APP_PORT: int = int(os.getenv("LEAD_APP_PORT", "8000"))
    WEB_UI_PORT: int = int(os.getenv("WEB_UI_PORT", "3000"))
    
    MCP_SCRIPT_WRITER_PATH: str = os.getenv("MCP_SCRIPT_WRITER_PATH", "../mcp-script-writer/src/server.py")
    MCP_IMAGE_GEN_PATH: str = os.getenv("MCP_IMAGE_GEN_PATH", "../mcp-image-gen/src/server.py")
    MCP_TTS_PATH: str = os.getenv("MCP_TTS_PATH", "../mcp-tts/src/server.py")
    MCP_VIDEO_GEN_PATH: str = os.getenv("MCP_VIDEO_GEN_PATH", "../mcp-video-gen/src/server.py")
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
