#!/bin/bash
set -e

# Activate virtual environment
source /opt/venv/bin/activate

# Function to log with timestamp
log_message() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $1"
}

# Function to wait for Ollama
wait_for_ollama() {
    log_message "Waiting for Ollama to be ready..."
    max_attempts=30
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags > /dev/null; then
            log_message "Ollama is ready!"
            return 0
        fi
        log_message "Attempt $attempt/$max_attempts: Ollama is not ready - sleeping 5s"
        sleep 5
        attempt=$((attempt + 1))
    done

    log_message "Ollama failed to start after $max_attempts attempts"
    return 1
}

# Function to pull models with progress tracking
pull_models() {
    log_message "Starting model downloads..."

    # Create a flag file to indicate download in progress
    touch /tmp/.models_downloading

    # Pull llama3.2:3b
    log_message "Pulling llama3.2:3b model..."
    curl -X POST http://localhost:11434/api/pull -d '{"name":"llama3.2:3b"}' || return 1
    log_message "llama3.2:3b model pulled successfully"

    # Pull nomic-embed-text
    log_message "Pulling nomic-embed-text model..."
    curl -X POST http://localhost:11434/api/pull -d '{"name":"nomic-embed-text"}' || return 1
    log_message "nomic-embed-text model pulled successfully"

    # Remove the downloading flag and create completion flag
    rm -f /tmp/.models_downloading
    touch /tmp/.models_ready
    log_message "All models downloaded successfully"
    return 0
}

# Function to verify models
verify_models() {
    log_message "Verifying models..."
    local models=$(curl -s http://localhost:11434/api/tags)
    if echo "$models" | grep -q "llama3.2:3b" && echo "$models" | grep -q "nomic-embed-text"; then
        log_message "All required models are present"
        return 0
    else
        log_message "Some models are missing"
        return 1
    fi
}

log_message "Starting initialization sequence..."

# Start Ollama in the background
log_message "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
if ! wait_for_ollama; then
    log_message "Failed to start Ollama"
    exit 1
fi

# Pull models
if ! pull_models; then
    log_message "Failed to pull models"
    exit 1
fi

# Verify models are present
if ! verify_models; then
    log_message "Model verification failed"
    exit 1
fi

# Create ready files
touch /tmp/.ollama_ready
log_message "Ollama and models initialization complete"

# Start supervisord
log_message "Starting FastAPI service..."
exec "$@"
