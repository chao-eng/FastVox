#!/bin/bash

# Configuration
ENV_NAME="fastvox"

echo "==== FastVox App Restart Script ===="

# 1. Kill old processes
echo "Checking for running FastVox backend processes..."

# Kill backend
PIDS=$(ps aux | grep "app.main" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Stopping old backend (PIDs: $PIDS)..."
    kill $PIDS
fi

sleep 1

# 2. Start all (use the existing start script)
if [ -f "scripts/start.sh" ]; then
    echo "Starting FastVox..."
    ./scripts/start.sh
else
    echo "Error: start.sh not found. Run scripts/setup_conda.sh first."
    exit 1
fi
