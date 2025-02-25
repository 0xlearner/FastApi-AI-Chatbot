import asyncio
import gc
import uuid
from typing import AsyncGenerator, Dict, List

from PyPDF2 import PdfReader

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

    def _create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        logger.debug(f"Creating chunks from text of length {len(text)}")
        chunks = []

        if len(text) <= self.chunk_size:
            chunks.append(text)
            logger.debug("Text fits in single chunk")
        else:
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                # Find the last period or newline in chunk_size range
                if end < len(text):
                    for break_char in [". ", "\n", ". ", ", ", " "]:
                        last_break = text[start:end].rfind(break_char)
                        if last_break != -1:
                            end = start + last_break + 1
                            break

                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                    logger.debug(
                        f"Created chunk {len(chunks)} with length {len(chunk)}"
                    )
                start = end - self.chunk_overlap

                # Force garbage collection periodically
                if len(chunks) % 10 == 0:
                    gc.collect()
                    logger.debug("Performed garbage collection")

        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks

    async def _process_page(self, page, page_num: int, file_path: str) -> List[Dict]:
        """Process a single page and return its chunks with metadata"""
        logger.info(f"Processing page {page_num + 1}")

        try:
            # Extract text
            text = page.extract_text()
            logger.debug(f"Extracted {len(text)} characters from page {page_num + 1}")

            if not text.strip():
                logger.warning(f"No text content found in page {page_num + 1}")
                return []

            # Create chunks
            chunks = self._create_chunks(text)
            logger.debug(f"Created {len(chunks)} chunks from page {page_num + 1}")

            # Create chunk dictionaries with metadata
            chunk_dicts = []
            for i, chunk in enumerate(chunks, 1):
                chunk_id = str(uuid.uuid4())
                chunk_dicts.append(
                    {
                        "text": chunk,
                        "metadata": {
                            "file_path": file_path,
                            "page_number": page_num + 1,
                            "chunk_id": chunk_id,
                            "chunk_number": i,
                        },
                    }
                )
                logger.debug(f"Created chunk dict {i} with ID {chunk_id}")

            logger.info(
                f"Successfully processed page {page_num + 1} into {len(chunk_dicts)} chunks"
            )
            return chunk_dicts

        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {str(e)}")
            return []

    async def process_pdf(self, file_path: str) -> AsyncGenerator[List[Dict], None]:
        """Process PDF and yield chunks in batches"""
        logger.info(f"Starting PDF processing for file: {file_path}")

        try:
            pdf_reader = PdfReader(file_path)
            total_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {total_pages} pages")

            current_batch = []
            processed_chunks = 0

            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    page_chunks = await self._process_page(page, page_num, file_path)

                    for chunk_dict in page_chunks:
                        current_batch.append(chunk_dict)
                        processed_chunks += 1
                        logger.debug(f"Added chunk {processed_chunks} to current batch")

                        if len(current_batch) >= self.batch_size:
                            logger.info(
                                f"Yielding batch of {len(current_batch)} chunks"
                            )
                            yield current_batch
                            current_batch = []
                            await asyncio.sleep(2)
                            gc.collect()
                            logger.debug("Performed garbage collection after batch")

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

            logger.info(
                f"Completed PDF processing. Total chunks processed: {processed_chunks}"
            )

        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}")
            raise Exception(f"Error processing PDF file: {str(e)}")
        finally:
            gc.collect()
            logger.info("Completed PDF processing and cleanup")
