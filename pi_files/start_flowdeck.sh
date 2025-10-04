#!/bin/bash

cd "$(dirname "$0")"

VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate

echo "Installing/updating dependencies..."
pip install "kivy[base]" kivy_examples requests &> /dev/null

echo "Starting FlowDeck..."
python3 pi_flowdeck_app.py

deactivate
