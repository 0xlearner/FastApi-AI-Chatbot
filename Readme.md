# FastAPI AI Chatbot

A minimalistic approach to building LLM-powered applications using FastAPI and Ollama. This project emphasizes direct control over core functionalities rather than relying on heavy abstractions from pre-made libraries.

## 🌟 Features

- **Minimalistic Architecture**: Direct implementation of core LLM functionalities without unnecessary abstractions
- **On-Premise LLM Integration**: Uses Ollama for local LLM deployment
- **PDF Processing**: Built-in support for document processing and chat
- **Custom Chunking**: Flexible document chunking implementation
- **Authentication**: Built-in authentication system
- **CORS Support**: Configured for cross-origin requests
- **Health Monitoring**: Endpoint for monitoring system health

## 🚀 Why This Approach?

While many libraries offer quick solutions for building LLM applications, they often come with heavy abstractions that limit flexibility and control. This project takes a minimalistic approach, giving you:

- Complete control over chunking strategies
- Freedom to implement custom similarity search algorithms
- Direct management of your data
- Better understanding of the underlying mechanisms
- Flexibility to enhance and modify core functionalities

## 🛠️ Technology Stack

- **Backend**: FastAPI
- **LLM Integration**: Ollama
- **Models**:
  - llama3.2:3b (for text generation)
  - nomic-embed-text (for embeddings)
- **Vector Database**: Pinecone
- **Database**: SQLite (easily adaptable to other databases)
- **Frontend**: HTML/JavaScript/HTMX with WebSocket support
- **Containerization**: Docker

## 📋 Prerequisites

- Docker
- Docker Compose (optional, but recommended)
- 8GB+ RAM (for running the LLM models)
- Pinecone API key

## 🔧 Installation & Setup

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/0xlearner/FastApi-AI-Chatbot.git
cd FastApi-AI-Chatbot
```

2. Build and run the Docker container:
```bash
docker build -t fastapi-ai-chatbot .
docker run -p 8000:8000 -p 11434:11434 fastapi-ai-chatbot
```

### Manual Setup

1. Install Python 3.12+
2. Install Ollama following instructions at [Ollama Installation](https://ollama.com/install)
3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the application:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🛠️ Make Commands

The project includes a comprehensive Makefile for easy management. Here are the available commands:

### Basic Commands

```bash
# Build the container
make build

# Start the container and services
make up

# Stop the container
make down

# Restart the container
make restart

# Remove container and volumes (clean slate)
make clean
```

### Monitoring & Debugging

```bash
# Check status of all services
make status

# View container logs
make logs

# View API logs specifically
make api-logs

# View API error logs
make api-err-logs

# Check all log files
make check-logs

# Start in debug mode
make debug

# Monitor model download progress
make download-progress
```

### Advanced Commands

```bash
# Access container shell
make shell

# Manually pull AI models
make models
```

### Quick Start

For the easiest setup, just run these two commands:

```bash
make build
make up
```

The `make up` command will:
1. Start the container
2. Wait for Ollama to initialize
3. Download required models (llama3.2:3b and nomic-embed-text)
4. Start the FastAPI server
5. Verify all services are running properly

You can monitor the status at any time with:
```bash
make status
```

### Service Health Indicators

The status command shows:
- 🟢 Container status
- 🟢 Model download status
- 🟢 FastAPI service status
- 🟢 Ollama service status

If you encounter any issues, use `make logs` or `make debug` for troubleshooting.

## 🔌 API Endpoints

- **Health Check**: `/health`
- **Authentication**: `/api/v1/auth/*`
- **Chat**: `/api/v1/chat/*`
- **PDF Processing**: `/api/v1/pdf/*`

## 💡 Usage

1. Start the server and ensure all models are loaded (check `/health` endpoint)
2. Upload PDF documents through the PDF processing endpoint
3. Start chatting with the documents using either:
   - REST API endpoints
   - WebSocket connection for real-time interaction

## 🛠️ Customization

### Chunking Strategy
Modify the chunking implementation in the PDF processing module to adjust how documents are split:
- Change chunk sizes
- Implement different chunking algorithms
- Add custom preprocessing steps

### Similarity Search
Customize the similarity search implementation:
- Implement different vector similarity algorithms
- Add filters and ranking methods
- Optimize for specific use cases

### Model Configuration
Update the Ollama configuration to:
- Use different models
- Adjust model parameters
- Implement model switching logic
