# Use slim Python image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps required by some Python packages and git for install-from-git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && pip install -r /app/requirements.txt

# Copy application code
COPY . /app

# Create a non-root user and use it
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Cloud Run provides PORT env. Use gunicorn as the entrypoint.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:$PORT", "app:app"]
