#!/bin/bash

# Configuration
ENV_NAME="fastvox"
PYTHON_VERSION="3.11"

echo "==== FastVox Conda Environment Setup ===="

# Check for conda
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed. Please install Miniconda or Anaconda first."
    exit 1
fi

# Create environment if it doesn't exist
if conda info --envs | grep -q "$ENV_NAME"; then
    echo "Environment '$ENV_NAME' already exists."
else
    echo "Creating conda environment '$ENV_NAME' with Python $PYTHON_VERSION..."
    conda create -y -n $ENV_NAME python=$PYTHON_VERSION
fi

# Activate environment and install dependencies
echo "Installing Python dependencies..."
# Note: we use 'conda run' or similar here because 'conda activate' inside a script requires shell initialization
conda run -n $ENV_NAME pip install -e .

echo ""
echo "==== Setup Complete! ===="
echo "To start the application, use the following commands:"
echo ""
echo "conda activate $ENV_NAME"
echo "python -m app.main"
