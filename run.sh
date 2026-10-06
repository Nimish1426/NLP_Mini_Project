#!/bin/bash
# CultureLens Run Script for macOS/Linux
# Starts the FastAPI server on http://localhost:8000

echo "Starting CultureLens server..."
echo "Open http://localhost:8000 in your browser."
echo "Press Ctrl+C to stop."
echo ""

source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
