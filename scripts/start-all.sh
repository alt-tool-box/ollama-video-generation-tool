#!/bin/bash

set -e

cd "$(dirname "$0")/.."
ROOT_DIR=$(pwd)

echo "=== Starting Video Creation App ==="

cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start MCP servers first (they need to be ready before lead-app calls them)
echo "Starting MCP Script Writer on port 9001..."
cd "$ROOT_DIR/apps/mcp-script-writer"
source .venv/bin/activate
python src/server.py &
deactivate 2>/dev/null || true

echo "Starting MCP Image Gen on port 9002..."
cd "$ROOT_DIR/apps/mcp-image-gen"
source .venv/bin/activate
python src/server.py &
deactivate 2>/dev/null || true

echo "Starting MCP TTS on port 9003..."
cd "$ROOT_DIR/apps/mcp-tts"
source .venv/bin/activate
python src/server.py &
deactivate 2>/dev/null || true

echo "Starting MCP Video Gen on port 9004..."
cd "$ROOT_DIR/apps/mcp-video-gen"
source .venv/bin/activate
python src/server.py &
deactivate 2>/dev/null || true

sleep 3

echo "Starting Lead App API on port 8000..."
cd "$ROOT_DIR/main-app/lead-app"
source .venv/bin/activate
python main.py &
LEAD_PID=$!

sleep 2

echo "Starting Web UI on port 3000..."
cd "$ROOT_DIR/main-app/web-ui"
npm run dev &
WEB_PID=$!

echo ""
echo "=== All services started ==="
echo ""
echo "  MCP Script Writer:  http://localhost:9001"
echo "  MCP Image Gen:      http://localhost:9002"
echo "  MCP TTS:            http://localhost:9003"
echo "  MCP Video Gen:      http://localhost:9004"
echo "  Lead App API:       http://localhost:8000"
echo "  Web UI:             http://localhost:3000"
echo "  API Docs:           http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

wait
