FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for SQLite and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browser binaries
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application source code
COPY . .

# Expose port for FastAPI backend
EXPOSE 8000

# Start development server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
