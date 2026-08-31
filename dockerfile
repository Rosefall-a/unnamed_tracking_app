FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into app/ subdirectory
COPY src/backend /app/app

# Copy and prepare the entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# On start: run pending migrations, then launch the app
ENTRYPOINT ["./entrypoint.sh"]