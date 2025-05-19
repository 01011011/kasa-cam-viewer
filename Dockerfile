# Use the official Python 3.12.6 runtime as a parent image
FROM python:3.12.6-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if needed, e.g., ffmpeg for video processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port (if your app serves a web interface, adjust as needed)
EXPOSE 8000

# Set environment variables (optional, if needed)
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]