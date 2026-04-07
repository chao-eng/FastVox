#!/bin/bash

# Configuration
ENV_NAME="fastvox"
# 自动切换到项目根目录
cd "$(dirname "$0")/.."
LOG_FILE="fastvox.log"

echo "==== FastVox App Background Start Script ===="

# 1. Port Check
echo "Checking port 8047..."
if lsof -Pi :8047 -sTCP:LISTEN -t >/dev/null ; then
    echo "Error: Port 8047 is already in use."
    exit 1
fi

# 2. Start building and then background the runner
echo "Building frontend..."
cd web && npm install && npm run build && cd ..

# 2. Start backend

echo "Starting backend in background (logging to $LOG_FILE)..."
export PYTHONPATH=$PYTHONPATH:.
nohup conda run --no-capture-output -n $ENV_NAME python -m app.main > $LOG_FILE 2>&1 &
PID=$!

echo "FastVox started in background (PID: $PID)."
echo "You can view logs with: tail -f $LOG_FILE"
echo "You can close this terminal window now."
