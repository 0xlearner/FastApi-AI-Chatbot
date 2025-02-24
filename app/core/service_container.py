from app.services.pdf_service import PDFService
from app.services.chat_service import ChatService
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.vector_store import PineconeStore
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.llm import OllamaLLM
from app.core.websocket_manager import WebSocketManager
from app.core.config import settings


class ServiceContainer:
    _instance = None

    def __init__(self):
        self.reset()
        # Initialize services immediately
        self.initialize_services()

    def reset(self):
        """Reset all services to None"""
        self.document_processor = None
        self.vector_store = None
        self.pdf_service = None
        self.chat_service = None
        self.embeddings = None
        self.llm = None
        self.websocket_manager = None

    def is_initialized(self) -> bool:
        """Check if all services are initialized"""
        return all([
            self.document_processor,
            self.vector_store,
            self.pdf_service,
            self.chat_service,
            self.embeddings,
            self.llm,
            self.websocket_manager
        ])

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize_services(self):
        # Initialize basic services first
        if not self.embeddings:
            self.embeddings = OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.EMBEDDING_MODEL_NAME,
            )

        if not self.llm:
            self.llm = OllamaLLM(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.LLM_MODEL_NAME
            )

        if not self.document_processor:
            self.document_processor = DocumentProcessor(
                upload_dir=settings.UPLOAD_DIR,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                batch_size=settings.BATCH_SIZE,
            )

        if not self.vector_store:
            self.vector_store = PineconeStore(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT,
                index_name=settings.PINECONE_INDEX_NAME,
            )

        if not self.websocket_manager:
            self.websocket_manager = WebSocketManager()

        # Initialize PDF service before chat service to break circular dependency
        if not self.pdf_service:
            self.pdf_service = PDFService(
                document_processor=self.document_processor,
                embeddings=self.embeddings,
                vector_store=self.vector_store,
                upload_dir=settings.UPLOAD_DIR,
                websocket_manager=self.websocket_manager,  # Add this
            )

        # Initialize chat service last
        if not self.chat_service:
            self.chat_service = ChatService(
                embeddings=self.embeddings,
                vector_store=self.vector_store,
                llm=self.llm,
                pdf_service=self.pdf_service,
            )


# Create and initialize the singleton instance
services = ServiceContainer.get_instance()
