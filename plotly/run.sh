#!/bin/bash

# Create a virtual environment called plotly-venv
python3 -m venv plotly-venv

# Activate the virtual environment
. plotly-venv/bin/activate

# Install dependencies
pip install -r plotly/requirements.txt

# Run the Dash app
python plotly/mini-plot-server.py