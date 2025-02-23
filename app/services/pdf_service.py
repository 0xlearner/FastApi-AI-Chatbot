from fastapi import HTTPException
from sqlalchemy.orm import Session
import os
from app.models.domain.pdf import PDF
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.vector_store import PineconeStore
from typing import List, Dict
import asyncio
from datetime import datetime
from app.core.websocket_manager import ConnectionManager


from app.utils.logging import get_service_logger

logger = get_service_logger("pdf_service")
ws_manager = ConnectionManager()

class PDFService:
    def __init__(
        self,
        document_processor: DocumentProcessor,
        embeddings: OllamaEmbeddings,
        vector_store: PineconeStore,
        upload_dir: str,
    ):
        self.document_processor = document_processor
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.upload_dir = upload_dir
        logger.info("PDFService initialized")

    async def verify_pdf_access(self, file_id: str, user_id: int, db: Session) -> bool:
        """Verify if a user has access to a specific PDF"""
        pdf = await self.get_pdf_by_id(file_id, db)
        return pdf is not None and pdf.user_id == user_id

    async def get_pdf_by_id(self, file_id: str, db: Session) -> PDF:
        """Get PDF by file_id"""
        return db.query(PDF).filter(PDF.file_id == file_id).first()

    async def process_chunk_batch(
        self, chunk_batch: List[Dict], file_id: str, total_chunks: int, processed_chunks: int, retries: int = 3
    ) -> bool:
        """Process a batch of chunks with retries and progress updates"""
        for attempt in range(retries):
            try:
                texts = [chunk["text"] for chunk in chunk_batch]

                # Generate embeddings
                embeddings = await self.embeddings.get_embeddings(texts)
                if not embeddings:
                    logger.error("Failed to generate embeddings")
                    continue

                # Store in vector database
                await self.vector_store.upsert_documents(embeddings, chunk_batch)
                
                # Calculate and send progress
                processed_chunks += len(chunk_batch)
                progress = min(int((processed_chunks / total_chunks) * 100), 100)
                await ws_manager.send_progress(file_id, {
                    "progress": progress,
                    "status": f"Processing chunks ({processed_chunks}/{total_chunks})"
                })
                
                logger.info(f"Processed and stored batch of {len(chunk_batch)} chunks")
                return True

            except Exception as e:
                logger.error(
                    f"Error processing chunk batch (attempt {attempt + 1}/{retries}): {str(e)}"
                )
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(1)

        return False

    async def process_saved_pdf(
        self,
        file_id: str,
        file_path: str,
        filename: str,
        content: bytes,
        user_id: int,
        db: Session
    ) -> PDF:
        """
        Process a saved PDF file.
        
        Args:
            file_id: The unique identifier for the file
            file_path: Path where the file is saved
            filename: Original filename
            content: File content
            user_id: The ID of the user who uploaded the file
            db: Database session
        """
        start_time = datetime.utcnow()
        logger.info(f"[{start_time}] Starting PDF processing for user {user_id}")

        try:
            # Initial progress update
            await ws_manager.send_progress(file_id, {
                "progress": 10,
                "status": "Starting PDF processing..."
            })

            # Process PDF in batches
            processed_chunks = 0
            failed_batches = 0
            max_failed_batches = 3

            # Count total chunks first
            total_chunks = 0
            chunk_count = 0
            
            await ws_manager.send_progress(file_id, {
                "progress": 15,
                "status": "Analyzing PDF structure..."
            })

            async for chunk_batch in self.document_processor.process_pdf(file_path):
                total_chunks += len(chunk_batch)
                chunk_count += 1
                if chunk_count % 5 == 0:
                    await ws_manager.send_progress(file_id, {
                        "progress": min(20 + (chunk_count // 5), 30),
                        "status": f"Analyzing content... ({total_chunks} segments found)"
                    })

            if total_chunks == 0:
                await ws_manager.send_progress(file_id, {
                    "progress": 0,
                    "status": "Error: No content found in PDF",
                    "error": "The PDF appears to be empty or unreadable"
                })
                raise HTTPException(status_code=500, detail="No content found in PDF")

            # Process chunks
            base_progress = 30
            remaining_progress = 60
            
            async for chunk_batch in self.document_processor.process_pdf(file_path):
                if not chunk_batch:
                    continue

                if await self.process_chunk_batch(chunk_batch, file_id, total_chunks, processed_chunks):
                    processed_chunks += len(chunk_batch)
                    current_progress = base_progress + int((processed_chunks / total_chunks) * remaining_progress)
                    await ws_manager.send_progress(file_id, {
                        "progress": current_progress,
                        "status": f"Processing segments: {processed_chunks}/{total_chunks}"
                    })
                else:
                    failed_batches += 1
                    if failed_batches >= max_failed_batches:
                        await ws_manager.send_progress(file_id, {
                            "progress": 0,
                            "status": "Error: Too many processing failures",
                            "error": "Failed to process PDF after multiple attempts"
                        })
                        raise HTTPException(
                            status_code=500, detail="Too many processing failures"
                        )

                await asyncio.sleep(0.1)

            # Create database record
            if processed_chunks > 0:
                await ws_manager.send_progress(file_id, {
                    "progress": 90,
                    "status": "Finalizing processing..."
                })

                pdf_db = PDF(
                    file_id=file_id,
                    filename=filename,
                    file_path=file_path,
                    user_id=user_id,
                )
                db.add(pdf_db)
                db.commit()
                db.refresh(pdf_db)

                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                logger.info(
                    f"[{end_time}] Successfully processed PDF: {filename} "
                    f"with {processed_chunks} chunks in {processing_time:.2f}s"
                )

                await ws_manager.send_progress(file_id, {
                    "progress": 100,
                    "status": "Complete",
                    "redirect": f"/chat/{file_id}"
                })
                
                return pdf_db
            else:
                if os.path.exists(file_path):
                    os.remove(file_path)
                await ws_manager.send_progress(file_id, {
                    "progress": 0,
                    "status": "Error: No segments processed",
                    "error": "Failed to process any content from the PDF"
                })
                raise HTTPException(
                    status_code=500, detail="Failed to process any chunks from the PDF"
                )

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            if os.path.exists(file_path):
                os.remove(file_path)
            await ws_manager.send_progress(file_id, {
                "progress": 0,
                "status": "Error",
                "error": str(e)
            })
            raise HTTPException(status_code=500, detail=str(e))