#!/bin/bash

# Start script for the Video Download & S3 Upload application

echo "Starting Video Download & S3 Upload Application..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from env.example..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "Please edit .env file with your S3 credentials before continuing."
        exit 1
    else
        echo "Error: env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create temp directory
mkdir -p tmp/jobs

# Start backend
echo "Starting backend server..."
cd backend
python main.py


