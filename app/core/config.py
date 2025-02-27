from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "PDF Chatbot"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database configurations
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    DROP_DB_ON_STARTUP: bool = True

    # Pinecone configurations
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str

    # Ollama configurations
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL_NAME: str = "llama3.2:3b"
    EMBEDDING_MODEL_NAME: str = "nomic-embed-text"

    # File storage
    UPLOAD_DIR: str = "uploads"

    CHUNK_SIZE: int = 10000  # Smaller chunks
    CHUNK_OVERLAP: int = 200  # Smaller overlap
    BATCH_SIZE: int = 5  # Smaller batches
    # EMBEDDING_BATCH_SIZE: int = 2  # Control embedding batch size
    # EMBEDDING_TIMEOUT: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
