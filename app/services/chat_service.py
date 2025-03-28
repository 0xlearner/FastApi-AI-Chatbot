from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.repositories.pdf_repository import PDFRepository
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.llm import OllamaLLM
from app.services.rag_pipeline.vector_store import PineconeStore
from app.utils.logging import get_service_logger

logger = get_service_logger("chat_service")


class ChatService:
    def __init__(
        self,
        embeddings: OllamaEmbeddings,
        vector_store: PineconeStore,
        llm: OllamaLLM,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.pdf_repository = PDFRepository()
        logger.info(f"[{datetime.utcnow()}] ChatService initialized")

    async def verify_pdf_access(self, file_id: str, user_id: int, db: Session) -> bool:
        """Verify if a user has access to a specific PDF"""
        return await self.pdf_repository.verify_pdf_access(file_id, user_id, db)

    async def get_chat_history(
        self,
        file_id: str,
        user_id: int,
        db: Session,
        limit: int = None
    ) -> List[Dict]:
        messages = self.chat_repository.get_chat_history(
            db, file_id, user_id, limit)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "sources": msg.sources,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

    async def save_message_pair(
        self,
        user_id: int,
        file_id: str,
        user_message: str,
        assistant_response: Dict,
        db: Session
    ):
        # Save user message
        self.chat_repository.save_message(
            db=db,
            user_id=user_id,
            file_id=file_id,
            content=user_message,
            role="user"
        )

        # Save assistant response
        self.chat_repository.save_message(
            db=db,
            user_id=user_id,
            file_id=file_id,
            content=assistant_response["response"],
            role="assistant",
            sources=assistant_response.get("sources")
        )

    async def get_response(self, query: str, file_id: str, db: Session) -> Dict:
        """Get a response for a query about a specific PDF"""
        try:
            start_time = datetime.utcnow()
            logger.info(
                f"[{start_time}] Processing query: '{
                    query}' for file_id: {file_id}"
            )

            # Generate query embedding
            query_embeddings = await self.embeddings.get_embeddings([query])

            # Retrieve relevant context
            results = await self.vector_store.similarity_search(
                query_embedding=query_embeddings[0],
                top_k=5,
                metadata_filter={"file_id": file_id},
                score_threshold=0.2,
                min_score_cutoff=0.3,
            )

            if not results:
                logger.warning(
                    f"No relevant context found for query '{
                        query}' in file {file_id}"
                )
                return {
                    "response": "I couldn't find any relevant information in the document to answer your question. "
                    "Could you try rephrasing your question or being more specific?",
                    "sources": [],
                }

            # Generate response using all relevant chunks
            response = await self.llm.generate_response(query, results)

            # Only include the highest scoring result in sources
            top_result = results[0]  # Results are already sorted by score
            sources = [
                {
                    "page_number": top_result["metadata"]["page_number"],
                    "file_path": top_result["metadata"]["file_path"],
                    "score": top_result["metadata"]["score"],
                    "text_preview": top_result["processed_text"][:100] + "...",
                }
            ]

            end_time = datetime.utcnow()
            logger.info(
                f"[{end_time}] Completed response generation. "
                f"Processing time: {
                    (end_time - start_time).total_seconds():.2f}s"
            )

            return {"response": response, "sources": sources}

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            raise
