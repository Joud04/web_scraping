# Use a slim Python 3.11 image
FROM python:3.11-slim

# Install system dependencies for crawl4ai and playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Note: Since crawl4ai was added manually, ensure it's in requirements or install it here
RUN pip install --no-cache-dir crawl4ai

# Install Playwright browsers (required by crawl4ai)
RUN playwright install --with-deps chromium

# Copy the project files
COPY . .

# Ensure the data and logs directories exist
RUN mkdir -p data logs

# Run the collector by default
CMD ["python", "-m", "src.collecteur.cli"]
