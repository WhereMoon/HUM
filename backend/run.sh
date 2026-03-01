#!/bin/bash
# Startup script for Digital Human backend

echo "Starting Digital Human Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
    echo "Continuing with default values..."
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run the server
python main.py
