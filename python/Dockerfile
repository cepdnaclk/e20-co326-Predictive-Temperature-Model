# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies required by numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application modules
COPY config.py .
COPY simulation.py .
COPY forecasting.py .
COPY mqtt_client.py .
COPY payloads.py .
COPY main.py .

# Run the main entry point
CMD ["python", "main.py"]