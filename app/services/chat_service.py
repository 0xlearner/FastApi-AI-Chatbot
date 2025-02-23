from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.vector_store import PineconeStore
from app.services.rag_pipeline.llm import OllamaLLM
from app.services.pdf_service import PDFService
from sqlalchemy.orm import Session
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        embeddings: OllamaEmbeddings,
        vector_store: PineconeStore,
        llm: OllamaLLM,
        pdf_service: PDFService,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.pdf_service = pdf_service
        logger.info("ChatService initialized")

    async def verify_pdf_access(self, file_id: str, user_id: int, db: Session) -> bool:
        """Verify if a user has access to a specific PDF"""
        return await self.pdf_service.verify_pdf_access(file_id, user_id, db)

    async def get_response(self, query: str, file_id: str, db: Session) -> Dict:
        """Get a response for a query about a specific PDF"""
        logger.info(f"Processing query: '{query}' for file_id: {file_id}")

        try:
            # Generate query embedding
            logger.debug("Generating query embedding")
            query_embeddings = await self.embeddings.get_embeddings([query])
            logger.debug(
                f"Generated embedding with dimension {len(query_embeddings[0])}"
            )

            # Retrieve relevant context with improved search
            logger.debug(
                f"Searching for relevant content with file_id filter: {file_id}"
            )
            results = await self.vector_store.similarity_search(
                query_embedding=query_embeddings[0],
                top_k=5,
                metadata_filter={"file_id": file_id},
                score_threshold=0.3,
            )

            if not results:
                logger.warning(
                    f"No relevant context found for query '{query}' in file {file_id}"
                )
                return {
                    "response": "I couldn't find any relevant information in the document to answer your question. "
                    "Could you try rephrasing your question or being more specific?",
                    "sources": [],
                }

            # Log search results
            logger.info(f"Found {len(results)} relevant chunks")
            for i, result in enumerate(results):
                logger.debug(
                    f"Result {i+1}: "
                    f"Score={result['metadata']['score']:.4f}, "
                    f"Page={result['metadata']['page_number']}, "
                    f"Length={len(result['text'])} chars"
                )

            # Generate response
            logger.debug("Generating response using LLM")
            response = await self.llm.generate_response(query, results)
            logger.info(f"Generated response of length {len(response)} characters")

            return {
                "response": response,
                "sources": [
                    {
                        "page_number": result["metadata"]["page_number"],
                        "file_path": result["metadata"]["file_path"],
                        "score": result["metadata"]["score"],
                        "text_preview": result["text"][:100]
                        + "...",  # Add text preview
                    }
                    for result in results
                ],
            }

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            raise
