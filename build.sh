#!/usr/bin/env bash
# Build script for Render deployment

echo "Starting build process..."

# Update package lists
apt-get update

# Install system dependencies for OCR and PDF processing
apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Build completed successfully!"
