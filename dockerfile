# Dockerfile for Backend Service (App)

# Use a robust Python base image
FROM python:3.12-slim

WORKDIR /app

# Install necessary system dependencies (postgresql client is good for networking/migrations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the app directory (assuming 'src' is relative to root)
COPY src/backend /app/app
COPY entrypoint.sh /app/entrypoint.sh

# Expose port 8000, where Uvicorn will run by default
EXPOSE 8000

# Command that runs when the container starts: 
# This command handles migrations first, then starts the FastAPI app using uvicorn.
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
ENTRYPOINT ["sh", "./entrypoint.sh"]