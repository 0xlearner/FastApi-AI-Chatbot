# Use Ubuntu as base image
FROM ubuntu:24.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=localhost:11434 \
    NLTK_DATA=/usr/local/share/nltk_data

# Install system dependencies and Python 3.12
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    python3.12-full \
    curl \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Update alternatives to use Python 3.12
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --set python3 /usr/bin/python3.12

# Set up working directory
WORKDIR /app

# Create virtual environment
RUN python3.12 -m venv /opt/venv

# Add virtual environment to PATH and activate it
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install pip, setuptools, and wheel in the virtual environment
RUN /opt/venv/bin/python3 -m pip install --upgrade pip setuptools wheel


# Install NLTK and download resources one by one with explicit SSL handling
RUN pip install --no-cache-dir nltk && \
    python3 -c "import nltk; \
    nltk.download('punkt_tab'); \
    nltk.download('averaged_perceptron_tagger'); \
    nltk.download('stopwords'); \
    nltk.download('wordnet')"


# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements and install in virtualenv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories
RUN mkdir -p /app/static/uploads \
    && mkdir -p /var/log/supervisor

# Copy and make the entrypoint script executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports
EXPOSE 8000 11434

# Set the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start services using supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# HEALTHCHECK
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health && \
    curl -f http://localhost:11434/api/tags || exit 1
