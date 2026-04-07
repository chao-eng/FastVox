#!/bin/bash

# Configuration
ENV_NAME="fastvox"

echo "==== FastVox Background Restart Script ===="

# 1. Kill old processes
echo "Checking for running FastVox backend processes..."

# Kill backend
PIDS=$(ps aux | grep "app.main" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Stopping old backend (PIDs: $PIDS)..."
    kill $PIDS
    sleep 2
fi

# 2. Start using daemon script
if [ -f "scripts/start_daemon.sh" ]; then
    echo "Starting FastVox in background..."
    ./scripts/start_daemon.sh
else
    echo "Error: start_daemon.sh not found."
    exit 1
fi
