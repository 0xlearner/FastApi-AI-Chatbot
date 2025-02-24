from typing import List
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.logging import get_pipeline_logger

logger = get_pipeline_logger("embeddings")


class OllamaEmbeddings:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        batch_size: int = 2,
        request_timeout: int = 30,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.batch_size = batch_size
        self.request_timeout = request_timeout
        self.semaphore = asyncio.Semaphore(2)  # Limit concurrent requests

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _get_single_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text with retry logic"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model_name, "prompt": text},
                    )
                    response.raise_for_status()
                    return response.json()["embedding"]
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                raise

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in smaller batches"""
        logger.info(f"Generating embeddings for {len(texts)} texts")
        all_embeddings = []

        # Process in smaller batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            logger.info(
                f"Processing batch {i//self.batch_size +
                                    1}/{-(-len(texts)//self.batch_size)}"
            )

            # Process batch concurrently but with rate limiting
            try:
                tasks = [self._get_single_embedding(text) for text in batch]
                batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle any exceptions in the batch
                for j, embedding in enumerate(batch_embeddings):
                    if isinstance(embedding, Exception):
                        logger.error(
                            f"Error in batch {
                                i//self.batch_size + 1}, item {j}: {str(embedding)}"
                        )
                        # Use zero vector as fallback
                        all_embeddings.append([0.0] * 768)
                    else:
                        all_embeddings.append(embedding)

                # Add delay between batches
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                # Fill failed batch with zero vectors
                all_embeddings.extend([[0.0] * 768] * len(batch))

        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings
