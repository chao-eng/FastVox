#!/bin/bash

# Configuration
ENV_NAME="fastvox"

echo "==== FastVox App Start Script ===="

# Check if conda environment exists
if ! conda info --envs | grep -q "$ENV_NAME"; then
    echo "Error: Conda environment '$ENV_NAME' not found. Please run scripts/setup_conda.sh first."
    exit 1
fi

# 1. Build frontend
if [ -d "web" ]; then
    echo "Updating frontend dependencies and building..."
    cd web && npm install && npm run build && cd ..
else
    echo "Warning: web directory not found, skipping build."
fi

# 2. Start backend
echo "Detected conda environment '$ENV_NAME'. Starting FastVox backend..."
conda run -n $ENV_NAME python -m app.main
