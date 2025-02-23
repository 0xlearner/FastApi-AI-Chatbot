from pinecone import Pinecone, Index
from typing import List, Dict, Any, Optional
import logging
from .text_processor import TextProcessor

logger = logging.getLogger(__name__)


class PineconeStore:
    def __init__(self, api_key: str, environment: str, index_name: str):
        pc = Pinecone(api_key=api_key)
        self.index = pc.Index(index_name)
        self.text_processor = TextProcessor()

    async def upsert_documents(
        self, embeddings: List[List[float]], documents: List[Dict]
    ):
        """Upsert documents and their embeddings to Pinecone"""
        logger.info(f"Starting upsert of {len(documents)} documents to Pinecone")

        try:
            vectors = []
            for i, (embedding, doc) in enumerate(zip(embeddings, documents)):
                # Process text for better searchability
                processed_text = self.text_processor.preprocess_text(doc["text"])
                keywords = self.text_processor.extract_keywords(doc["text"])

                metadata = {
                    "text": doc["text"],
                    "processed_text": processed_text,
                    "keywords": keywords,
                    "file_path": doc["metadata"]["file_path"],
                    "page_number": doc["metadata"]["page_number"],
                    "file_id": doc["metadata"]["file_path"]
                    .split("/")[-1]
                    .split("_")[0],
                }

                vectors.append(
                    {
                        "id": doc["metadata"]["chunk_id"],
                        "values": embedding,
                        "metadata": metadata,
                    }
                )

            # Upsert to Pinecone
            self.index.upsert(vectors=vectors)
            logger.info(f"Successfully completed upsert of {len(documents)} documents")

        except Exception as e:
            logger.error(f"Error during Pinecone upsert: {str(e)}")
            raise

    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.15,  # Lowered threshold to get more results
    ) -> List[Dict]:
        """Perform similarity search with improved filtering and scoring"""
        try:
            logger.info(f"Searching with filter: {metadata_filter}")

            # Query Pinecone with higher top_k for post-processing
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k * 3,  # Get more results for post-processing
                include_metadata=True,
                filter=metadata_filter,
            )

            # Post-process results
            formatted_results = []
            for match in results.matches:
                if match.score < score_threshold:
                    continue

                formatted_results.append(
                    {
                        "text": match.metadata["text"],
                        "metadata": {
                            "file_path": match.metadata["file_path"],
                            "page_number": match.metadata["page_number"],
                            "score": float(match.score),  # Ensure score is float
                            "chunk_index": match.metadata.get("chunk_index", 0),
                        },
                    }
                )

            # Sort by score and take top_k
            formatted_results.sort(key=lambda x: x["metadata"]["score"], reverse=True)
            formatted_results = formatted_results[:top_k]

            # Log result details
            logger.info(
                f"Found {len(formatted_results)} results above threshold {score_threshold}"
            )
            for i, result in enumerate(formatted_results):
                logger.debug(
                    f"Result {i+1}: Score={result['metadata']['score']:.4f}, "
                    f"Page={result['metadata']['page_number']}"
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}", exc_info=True)
            raise
