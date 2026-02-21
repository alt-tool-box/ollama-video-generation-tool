# Video Creation App

A modular AI video creation system that generates motion videos from text prompts. Uses local models (Ollama, ComfyUI, Coqui TTS) with optional cloud TTS (ElevenLabs). Features a two-phase workflow: script approval before resource-intensive generation.

---

## Features

- **Prompt enhancement** — Improves short user prompts before script generation
- **AI script generation** — Creates structured video scripts with scenes (Ollama)
- **Motion video clips** — AnimateDiff via ComfyUI (characters and scenes in motion)
- **Dual TTS** — ElevenLabs (primary) with Coqui XTTS v2 (local fallback)
- **Final render** — FFmpeg/MoviePy with crossfades, audio normalization, optional background music
- **Real-time progress** — WebSocket updates during generation
- **Two-phase workflow** — Review and approve script before generating video

---

## Tech Stack

| Component | Technology |
|-----------|-------------|
| Lead App | Python, FastAPI |
| Web UI | React, TypeScript, Vite, TailwindCSS |
| Script Writer | Ollama (`deepseek-r1:14b`) |
| Video Clips | ComfyUI + AnimateDiff (SD 1.5 + motion module) |
| TTS | ElevenLabs (primary) / Coqui XTTS v2 (fallback) |
| Video Render | FFmpeg, MoviePy |
| Database | PostgreSQL |
| Queue | Redis |
| Storage | MinIO (S3-compatible) |

---

## Models Used

| Purpose | Model | Source | Config |
|---------|-------|--------|--------|
| **Script generation** | `deepseek-r1:14b` | Ollama | `OLLAMA_MODEL` |
| **Motion video (base)** | `realisticVisionV60B1_v51VAE.safetensors` | ComfyUI checkpoints | SD 1.5 for AnimateDiff |
| **Motion video (motion)** | `mm_sd_v15_v2.ckpt` | ComfyUI animatediff_models | AnimateDiff motion module |
| **Static image (legacy)** | `sd_xl_base_1.0.safetensors` | ComfyUI checkpoints | SDXL for `generate_image` |
| **TTS (primary)** | `eleven_multilingual_v2` | ElevenLabs API | `ELEVENLABS_MODEL_ID` |
| **TTS (fallback)** | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui (auto-download) | `TTS_MODEL` |

Video rendering uses FFmpeg (libx264, AAC) and MoviePy — no AI models.

---

## Prerequisites

Install these before setup:

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ (3.10 for mcp-tts, 3.11+ for others) | Backend services |
| Node.js | 18+ | Web UI |
| FFmpeg | Latest | Video/audio processing |
| PostgreSQL | 14+ | Job and script storage |
| Redis | 6+ | Queue |
| MinIO | Latest | Object storage (clips, audio, final video) |
| Ollama | Latest | LLM for script generation |
| ComfyUI | With AnimateDiff-Evolved | Motion video generation |

---

## Tool Installation Guide

Install the required tools before running the app. Commands below work on **macOS** (Homebrew) and **Linux** (apt/dnf).

### FFmpeg

Video and audio encoding/decoding.

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y ffmpeg
```

**Fedora/RHEL:**
```bash
sudo dnf install -y ffmpeg
```

**Verify:** `ffmpeg -version`

---

### Python

Backend services. Use Python 3.10 for `mcp-tts`, 3.11+ for others.

**macOS (Homebrew):**
```bash
brew install python@3.11 python@3.10
```

**Ubuntu/Debian:**
```bash
sudo apt install -y python3.11 python3.11-venv python3.10 python3.10-venv
```

**Fedora/RHEL:**
```bash
sudo dnf install -y python3.11 python3.10
```

**Verify:** `python3 --version` and `python3.10 --version`

---

### Node.js

Web UI build and dev server.

**macOS (Homebrew):**
```bash
brew install node
```

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**Fedora/RHEL:**
```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
```

**Verify:** `node --version` (18+)

---

### PostgreSQL

Database for jobs and scripts.

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Fedora/RHEL:**
```bash
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
```

**Create database:** `createdb video_creation` (as postgres user)

---

### Redis

Queue and caching.

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
```

**Fedora/RHEL:**
```bash
sudo dnf install -y redis
sudo systemctl start redis
```

**Verify:** `redis-cli ping` → `PONG`

---

### MinIO

S3-compatible object storage for clips, audio, and final video.

**macOS (Homebrew):**
```bash
brew install minio/stable/minio
minio server ~/minio-data &
```

**Linux (binary):**
```bash
curl -O https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server ~/minio-data &
```

**Docker (any OS):**
```bash
docker run -d -p 9000:9000 -p 9001:9001 --name minio \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

Create bucket `video-creation` via MinIO Console (http://localhost:9001) or `mc mb local/video-creation`.

---

### Ollama

Local LLM for script generation.

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Pull model:**
```bash
ollama run deepseek-r1:14b
```

---

### ComfyUI

Motion video generation with AnimateDiff.

1. **Clone ComfyUI:**
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   pip install -r requirements.txt
   ```

2. **Install custom nodes:**
   ```bash
   cd custom_nodes
   git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved
   git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
   pip install -r ComfyUI-AnimateDiff-Evolved/requirements.txt
   pip install -r ComfyUI-VideoHelperSuite/requirements.txt
   ```

3. **Download models** (see [Quick Setup](#5-download-comfyui-models) step 5).

4. **Run ComfyUI:**
   ```bash
   python main.py --listen 0.0.0.0 --port 8188
   ```

---

## Quick Setup

### 1. Clone and enter project

```bash
cd ollama-video-creation
```

### 2. Run setup script

```bash
./scripts/setup.sh
```

This installs Python dependencies for all services and npm packages for the Web UI.

### 3. Configure environment

Copy the example env files and fill in your values:

```bash
# Root config (used by MCP apps via shared/)
cp .env.example .env

# Lead App
cp main-app/lead-app/.env.example main-app/lead-app/.env

# MCP services
for app in mcp-script-writer mcp-image-gen mcp-tts mcp-video-gen; do
  cp apps/$app/.env.example apps/$app/.env
done
```

Edit each `.env` with your database credentials, MinIO keys, and optional ElevenLabs API key. See [Environment Variables](#environment-variables) below.

### 4. Start infrastructure

Ensure these are running:

- **PostgreSQL** — Create database: `createdb video_creation`
- **Redis** — Default port 6379
- **MinIO** — Default port 9000, create bucket `video-creation`
- **Ollama** — `ollama run deepseek-r1:14b` (pull model if needed)
- **ComfyUI** — With AnimateDiff-Evolved and VideoHelperSuite custom nodes

### 5. Download ComfyUI models

Place these in your ComfyUI installation:

| Model | Path | Size |
|-------|------|------|
| SD 1.5 checkpoint | `ComfyUI/models/checkpoints/realisticVisionV60B1_v51VAE.safetensors` | ~2GB |
| AnimateDiff motion | `ComfyUI/models/animatediff_models/mm_sd_v15_v2.ckpt` | ~1.8GB |

### 6. Start all services

```bash
./scripts/start-all.sh
```

### 7. Open the app

- **Web UI:** http://localhost:3000  
- **API docs:** http://localhost:8000/docs  

---

## Environment Variables

### Root `.env` (shared by MCP apps)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection (asyncpg) | `postgresql+asyncpg://user:pass@localhost:5432/video_creation` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | MinIO host | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET` | Bucket name | `video-creation` |
| `MINIO_SECURE` | Use HTTPS | `false` |
| `OLLAMA_URL` | Ollama API URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Script generation model | `deepseek-r1:14b` |
| `COMFYUI_URL` | ComfyUI API URL | `http://localhost:8188` |
| `TTS_MODEL` | Coqui model (fallback TTS) | `tts_models/multilingual/multi-dataset/xtts_v2` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Lead App `main-app/lead-app/.env`

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Same as root | |
| `REDIS_URL` | Same as root | |
| `MINIO_*` | Same as root | |
| `LEAD_APP_PORT` | Lead app port | `8000` |
| `WEB_UI_PORT` | Web UI port | `3000` |
| `MCP_SCRIPT_WRITER_URL` | Script writer SSE endpoint | `http://localhost:9001/sse` |
| `MCP_IMAGE_GEN_URL` | Image gen SSE endpoint | `http://localhost:9002/sse` |
| `MCP_TTS_URL` | TTS SSE endpoint | `http://localhost:9003/sse` |
| `MCP_VIDEO_GEN_URL` | Video gen SSE endpoint | `http://localhost:9004/sse` |

### TTS `apps/mcp-tts/.env`

| Variable | Description | Example |
|----------|-------------|---------|
| `PORT` | TTS server port | `9003` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (empty = Coqui only) | `sk_...` |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID | `7qBNUtXRGP0jPi0H4r8k` |
| `ELEVENLABS_MODEL_ID` | ElevenLabs model | `eleven_multilingual_v2` |
| `TTS_MODEL` | Coqui fallback model | `tts_models/multilingual/multi-dataset/xtts_v2` |
| `MINIO_*` | MinIO config (if different from root) | |

### Video Gen `apps/mcp-video-gen/.env`

| Variable | Description | Example |
|----------|-------------|---------|
| `PORT` | Video gen server port | `9004` |
| `BACKGROUND_MUSIC_PATH` | MinIO path to background music (optional) | `music/ambient.mp3` |
| `BACKGROUND_MUSIC_VOLUME` | Volume 0–1 | `0.15` |
| `MINIO_*` | MinIO config | |

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| MCP Script Writer | 9001 | http://localhost:9001 |
| MCP Image Gen | 9002 | http://localhost:9002 |
| MCP TTS | 9003 | http://localhost:9003 |
| MCP Video Gen | 9004 | http://localhost:9004 |
| Lead App API | 8000 | http://localhost:8000 |
| Web UI | 3000 | http://localhost:3000 |
| ComfyUI | 8188 | http://localhost:8188 |
| Ollama | 11434 | http://localhost:11434 |
| MinIO | 9000 | http://localhost:9000 |

---

## Workflow

1. **Enter prompt** — User enters a short prompt (e.g. "a cat in space").
2. **Enhance prompt** — Script writer improves the prompt for better results.
3. **Generate script** — LLM creates scenes with narration and visual descriptions.
4. **Review & approve** — User can edit, regenerate scenes, or approve.
5. **Generate video** — On approval:
   - Motion clips (AnimateDiff) → MinIO
   - TTS audio (ElevenLabs or Coqui) → MinIO
   - Final render (clips + audio + transitions) → MinIO
6. **Play video** — Web UI loads the final video via presigned URL.

---

## Project Structure

```
ollama-video-creation/
├── main-app/                 # Self-contained (Lead App + Web UI)
│   ├── lead-app/             # FastAPI orchestrator (:8000)
│   └── web-ui/               # React frontend (:3000)
├── apps/                     # MCP HTTP servers
│   ├── mcp-script-writer/    # :9001 - Ollama script generation
│   ├── mcp-image-gen/        # :9002 - ComfyUI AnimateDiff clips
│   ├── mcp-tts/              # :9003 - ElevenLabs + Coqui TTS
│   └── mcp-video-gen/        # :9004 - FFmpeg/MoviePy render
├── shared/                   # Python utils (apps only)
│   └── python/               # config, minio_client, logger
├── scripts/
│   ├── setup.sh              # Install all dependencies
│   └── start-all.sh         # Start all 6 services
├── ComfyUI/                  # ComfyUI installation (separate)
├── .env                      # Root config
└── .env.example
```

---

## Troubleshooting

### WebSocket not connecting

- Ensure Lead App is running on port 8000.
- Check browser console for CORS or connection errors.
- Verify `LEAD_APP_PORT` matches the port the API uses.

### ElevenLabs not used (Coqui fallback)

- Set `ELEVENLABS_API_KEY` in `apps/mcp-tts/.env`.
- Restart the TTS MCP server after changing `.env`.
- Confirm the `.env` is loaded (MCP servers load `apps/mcp-tts/.env` at startup).

### ComfyUI / AnimateDiff errors

- Ensure ComfyUI-AnimateDiff-Evolved and VideoHelperSuite are installed.
- Check checkpoint path: `realisticVisionV60B1_v51VAE.safetensors` in `models/checkpoints/`.
- Check motion module: `mm_sd_v15_v2.ckpt` in `models/animatediff_models/`.

### Database connection failed

- Create database: `createdb video_creation`
- Verify `DATABASE_URL` in root `.env` and `main-app/lead-app/.env`.

### MinIO upload errors

- Create bucket `video-creation` in MinIO.
- Verify `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` in each `.env`.

---

## Documentation

- [PLAN.md](PLAN.md) — Project plan, MCP tools, database schema
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture diagrams (Mermaid)