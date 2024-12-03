# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
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

# Run the bot
CMD ["python", "the_alt_signal_telegram_bot.py"] 