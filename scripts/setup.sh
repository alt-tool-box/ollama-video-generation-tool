#!/bin/bash

set -e

echo "=== Video Creation App Setup ==="

cd "$(dirname "$0")/.."
ROOT_DIR=$(pwd)

# Function to setup Python app with its own venv
setup_python_app() {
    local app_name=$1
    local app_path=$2

    echo "Setting up $app_name..."
    cd "$app_path"

    if [ ! -d ".venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv .venv
    fi

    echo "  Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt -q
    deactivate

    echo "  Done!"
}

echo ""
echo "=== Installing MCP Server dependencies ==="

setup_python_app "mcp-script-writer" "$ROOT_DIR/apps/mcp-script-writer"
setup_python_app "mcp-image-gen" "$ROOT_DIR/apps/mcp-image-gen"
setup_python_app "mcp-tts" "$ROOT_DIR/apps/mcp-tts"
setup_python_app "mcp-video-gen" "$ROOT_DIR/apps/mcp-video-gen"

echo ""
echo "=== Installing Lead App dependencies ==="

setup_python_app "lead-app" "$ROOT_DIR/main-app/lead-app"

echo ""
echo "=== Installing Web UI dependencies ==="
cd "$ROOT_DIR/main-app/web-ui"
npm install

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Review .env files in main-app/lead-app/ and apps/mcp-*/"
echo "2. Ensure PostgreSQL, Redis, MinIO, and Ollama are running"
echo "3. Create the database: createdb video_creation"
echo "4. Run: ./scripts/start-all.sh"
