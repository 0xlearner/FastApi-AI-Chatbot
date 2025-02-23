from PyPDF2 import PdfReader
from typing import List, Dict, AsyncGenerator
import uuid
import os
import logging
import asyncio
import gc
from datetime import datetime

from app.utils.logging import get_pipeline_logger

logger = get_pipeline_logger("document_processor")


class DocumentProcessor:
    def __init__(
        self,
        upload_dir: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        batch_size: int = 2,
    ):
        self.upload_dir = upload_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        logger.info(
            f"DocumentProcessor initialized with chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}, batch_size={batch_size}"
        )

    async def process_pdf(self, file_path: str) -> AsyncGenerator[List[Dict], None]:
        """Process PDF and yield chunks in batches"""
        start_time = datetime.utcnow()
        logger.info(f"[{start_time}] Starting PDF processing for file: {file_path}")

        try:
            # Validate PDF file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            pdf_reader = PdfReader(file_path)
            if len(pdf_reader.pages) == 0:
                raise ValueError("PDF file is empty")

            total_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {total_pages} pages")

            current_batch = []
            processed_chunks = 0

            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    if not text.strip():
                        logger.warning(f"Page {page_num + 1} is empty")
                        continue

                    chunks = self._create_chunks(text)

                    for chunk in chunks:
                        if not chunk.strip():
                            continue

                        chunk_dict = {
                            "text": chunk,
                            "metadata": {
                                "file_path": file_path,
                                "page_number": page_num + 1,
                                "chunk_id": str(uuid.uuid4()),
                            },
                        }

                        current_batch.append(chunk_dict)
                        processed_chunks += 1

                        if len(current_batch) >= self.batch_size:
                            logger.info(
                                f"Yielding batch of {len(current_batch)} chunks"
                            )
                            yield current_batch
                            current_batch = []
                            await asyncio.sleep(0.1)  # Prevent overload
                            gc.collect()  # Force garbage collection

                    logger.info(
                        f"Completed processing page {page_num + 1}/{total_pages}"
                    )

                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                    continue

            # Yield any remaining chunks
            if current_batch:
                logger.info(f"Yielding final batch of {len(current_batch)} chunks")
                yield current_batch

            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            logger.info(
                f"[{end_time}] Completed PDF processing. "
                f"Total chunks: {processed_chunks}, "
                f"Time: {processing_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}", exc_info=True)
            raise

    def _create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        chunks = []

        if not text:
            return chunks

        if len(text) <= self.chunk_size:
            chunks.append(text)
            return chunks

        start = 0
        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                # Find the last sentence break
                for break_char in [". ", "\n", ". ", ", ", " "]:
                    last_break = text[start:end].rfind(break_char)
                    if last_break != -1:
                        end = start + last_break + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap

            if len(chunks) % 10 == 0:
                gc.collect()

        return chunks
