#!/bin/bash
# CultureLens Setup Script for macOS/Linux
# Creates a virtual environment, installs dependencies, and downloads the spaCy model.

set -e

echo "============================================"
echo "  CultureLens - Setup Script (macOS/Linux)"
echo "============================================"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/4] Virtual environment already exists, skipping creation."
fi

# Activate and install requirements
echo "[2/4] Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

# Download spaCy model
echo "[3/4] Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Train the ML classifier
echo "[4/4] Training the ML classifier..."
python scripts/train_classifier.py || echo "WARNING: ML classifier training failed. The system will try to auto-train on first run."

echo ""
echo "============================================"
echo "  Setup complete! Run './run.sh' to start."
echo "============================================"
