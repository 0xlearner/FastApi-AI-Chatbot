from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import aiofiles
import os
from app.models.domain.pdf import PDF
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.vector_store import PineconeStore
from typing import List, Dict
import uuid
import logging
import asyncio
from datetime import datetime

from app.utils.logging import get_service_logger

logger = get_service_logger("pdf_service")


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
        self, chunk_batch: List[Dict], retries: int = 3
    ) -> bool:
        """Process a batch of chunks with retries"""
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
                logger.info(f"Processed and stored batch of {len(chunk_batch)} chunks")
                return True

            except Exception as e:
                logger.error(
                    f"Error processing chunk batch (attempt {attempt + 1}/{retries}): {str(e)}"
                )
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(1)  # Wait before retrying

        return False

    async def save_and_process_pdf(
        self, file: UploadFile, user_id: int, db: Session
    ) -> PDF:
        start_time = datetime.utcnow()
        logger.info(f"[{start_time}] Starting PDF processing for user {user_id}")

        # Create user directory if it doesn't exist
        user_dir = os.path.join(self.upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # Generate unique file ID and save file
        file_id = str(uuid.uuid4())
        file_path = os.path.join(user_dir, f"{file_id}_{file.filename}")

        try:
            # Save file to disk
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            logger.info(f"[{datetime.utcnow()}] File saved: {file_path}")

            # Process PDF in batches
            processed_chunks = 0
            failed_batches = 0
            max_failed_batches = 3

            async for chunk_batch in self.document_processor.process_pdf(file_path):
                if not chunk_batch:
                    logger.warning("Received empty chunk batch")
                    continue

                if await self.process_chunk_batch(chunk_batch):
                    processed_chunks += len(chunk_batch)
                else:
                    failed_batches += 1
                    if failed_batches >= max_failed_batches:
                        raise HTTPException(
                            status_code=500, detail="Too many processing failures"
                        )

                # Add delay between batches to prevent overload
                await asyncio.sleep(0.5)

            # Only create database record if we processed some chunks successfully
            if processed_chunks > 0:
                pdf_db = PDF(
                    file_id=file_id,
                    filename=file.filename,
                    file_path=file_path,
                    user_id=user_id,
                )
                db.add(pdf_db)
                db.commit()
                db.refresh(pdf_db)

                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                logger.info(
                    f"[{end_time}] Successfully processed PDF: {file.filename} "
                    f"with {processed_chunks} chunks in {processing_time:.2f}s"
                )
                return pdf_db
            else:
                # Clean up file if no chunks were processed
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(
                    status_code=500, detail="Failed to process any chunks from the PDF"
                )

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            # Clean up file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=str(e))
