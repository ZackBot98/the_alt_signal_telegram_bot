# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code and .env file
COPY the_alt_signal_telegram_bot.py .
COPY .env .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=UTF-8
ENV TINI_SUBREAPER=true

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "-s", "--"]

# Create volume for logs
VOLUME ["/app/logs"]

# Run the bot
CMD ["python", "-u", "the_alt_signal_telegram_bot.py"]