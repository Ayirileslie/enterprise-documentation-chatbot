# Use Python 3.10.18-slim as the base image
FROM python:3.10.18-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    python3-dev \
    libffi-dev \
    gcc \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential pkg-config python3-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install specific versions of build tools
RUN pip install --no-cache-dir pip==24.2 setuptools==75.1.0 wheel==0.44.0

# Copy requirements.txt
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data/documents data/chroma_db logs

# Expose the port that the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
