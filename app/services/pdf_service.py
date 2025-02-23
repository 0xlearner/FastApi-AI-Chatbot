from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import aiofiles
import os
from app.models.domain.pdf import PDF
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.vector_store import PineconeStore
from typing import List, Dict, Optional
import uuid
import logging
import asyncio

logger = logging.getLogger(__name__)


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

    async def verify_pdf_access(self, file_id: str, user_id: int, db: Session) -> bool:
        """Verify if a user has access to a specific PDF"""
        pdf = await self.get_pdf_by_id(file_id, db)
        return pdf is not None and pdf.user_id == user_id

    async def get_pdf_by_id(self, file_id: str, db: Session) -> Optional[PDF]:
        """Get a PDF by its file_id"""
        return db.query(PDF).filter(PDF.file_id == file_id).first()

    async def get_user_pdfs(self, user_id: int, db: Session) -> List[PDF]:
        """Get all PDFs for a specific user"""
        return db.query(PDF).filter(PDF.user_id == user_id).all()

    async def process_chunk_batch(self, chunk_batch: List[Dict]) -> bool:
        """Process a batch of chunks with error handling"""
        try:
            texts = [chunk["text"] for chunk in chunk_batch]
            embeddings = await self.embeddings.get_embeddings(texts)
            await self.vector_store.upsert_documents(embeddings, chunk_batch)
            logger.info(f"Processed and stored batch of {len(chunk_batch)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error processing chunk batch: {str(e)}")
            return False

    async def save_and_process_pdf(
        self, file: UploadFile, user_id: int, db: Session
    ) -> PDF:
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

            logger.info("Starting PDF processing and embedding generation")

            # Process PDF in batches using async generator
            processed_chunks = 0
            failed_batches = 0

            async for chunk_batch in self.document_processor.process_pdf(file_path):
                if await self.process_chunk_batch(chunk_batch):
                    processed_chunks += len(chunk_batch)
                else:
                    failed_batches += 1

                # Add delay between batch processing
                await asyncio.sleep(1)

                # If too many failures, abort
                if failed_batches > 3:
                    raise HTTPException(
                        status_code=500, detail="Too many failures during processing"
                    )

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

                logger.info(
                    f"Successfully processed PDF: {file.filename} with {processed_chunks} chunks"
                )
                return pdf_db
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to process any chunks from the PDF"
                )

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            # Clean up file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=500, detail=f"Error processing PDF: {str(e)}"
            )
