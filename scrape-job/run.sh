#!/bin/bash
# Source conda initialization script - adjust the path as needed.
if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
    source "/opt/conda/etc/profile.d/conda.sh"
fi

# Name of the environment and desired Python version.
ENV_NAME="scraper"
PYTHON_VERSION="3.10"

# Function to check if conda environment exists.
env_exists() {
    conda info --envs | awk '{print $1}' | grep -qx "$ENV_NAME"
}

# Check if environment exists; if not, create it.
if env_exists; then
    echo "Conda environment '$ENV_NAME' already exists. Activating..."
else
    echo "Conda environment '$ENV_NAME' does not exist. Creating..."
    conda create -n "$ENV_NAME" python="$PYTHON_VERSION" -y || { echo "Failed to create environment"; exit 1; }
fi

conda activate "$ENV_NAME" || { echo "Failed to activate environment"; exit 1; }

# Install Python packages using pip.
echo "Installing packages..."
pip install fastapi
pip install uvicorn
pip install edgartools
pip install requests

# Start the uvicorn server.
echo "Starting uvicorn server..."
python main.py --host 0.0.0.0 --port 8787