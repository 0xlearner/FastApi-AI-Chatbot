from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.rag_pipeline.text_processor import TextProcessor
from app.utils.logging import get_pipeline_logger

logger = get_pipeline_logger("vector_store")


class PineconeStore:
    def __init__(self, api_key: str, environment: str, index_name: str):
        pc = Pinecone(api_key=api_key)
        self.index = pc.Index(index_name)
        self.text_processor = TextProcessor()
        logger.info(f"Initialized PineconeStore with index: {index_name}")

    async def upsert_documents(
        self, embeddings: List[List[float]], documents: List[Dict]
    ):
        """Upsert documents and their embeddings to Pinecone"""
        logger.info(f"Starting upsert of {
                    len(documents)} documents to Pinecone")

        try:
            vectors = []
            for i, (embedding, doc) in enumerate(zip(embeddings, documents)):
                # Process text for better searchability
                processed_text = self.text_processor.preprocess_text(
                    doc["text"])
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
            logger.info(f"Successfully completed upsert of {
                        len(documents)} documents")

        except Exception as e:
            logger.error(f"Error during Pinecone upsert: {str(e)}")
            raise

    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.2,
        min_score_cutoff: float = 0.3,  # Added minimum score threshold
    ) -> List[Dict]:
        """
        Perform similarity search with improved filtering and scoring
        """
        try:
            start_time = datetime.utcnow()
            logger.info(
                f"[{start_time}] Starting similarity search with filter: {
                    metadata_filter}"
            )

            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k * 2,  # Get more results for filtering
                include_metadata=True,
                include_values=True,
                filter=metadata_filter,
            )

            logger.info(f"Got {len(results.matches)
                               } initial matches from Pinecone")

            # Find the highest score
            if results.matches:
                max_score = max(match.score for match in results.matches)
                logger.info(f"Highest similarity score: {max_score:.4f}")
            else:
                logger.warning("No matches found")
                return []

            # Only keep results close to the highest score
            score_cutoff = max(
                min_score_cutoff, max_score * 0.8
            )  # Within 80% of max score

            # Post-process results
            processed_results = []
            for match in results.matches:
                # Skip results below threshold or cutoff
                if match.score < score_threshold or match.score < score_cutoff:
                    continue

                processed_result = {
                    "text": match.metadata["text"],
                    "metadata": {
                        "file_path": match.metadata["file_path"],
                        "page_number": match.metadata["page_number"],
                        "score": float(match.score),
                        "file_id": match.metadata["file_id"],
                    },
                }

                # Add processed_text if available
                if "processed_text" in match.metadata:
                    processed_result["processed_text"] = match.metadata[
                        "processed_text"
                    ]

                logger.debug(
                    f"Match score: {match.score:.4f}, "
                    f"Page: {match.metadata['page_number']}, "
                    f"Preview: {match.metadata['processed_text'][:100]}..."
                )

                processed_results.append(processed_result)

            # Sort by score and take top_k
            processed_results.sort(
                key=lambda x: x["metadata"]["score"], reverse=True)
            processed_results = processed_results[:top_k]

            end_time = datetime.utcnow()
            logger.info(
                f"[{end_time}] Returning {len(processed_results)} results "
                f"above score cutoff {score_cutoff:.4f}"
            )

            # Log the final selected results
            for i, result in enumerate(processed_results):
                logger.info(
                    f"Result {i+1}: "
                    f"Score={result['metadata']['score']:.4f}, "
                    f"Page={result['metadata']['page_number']}, "
                    f"Delta from max={max_score -
                                      result['metadata']['score']:.4f}"
                )

            return processed_results

        except Exception as e:
            logger.error(f"Error during similarity search: {
                         str(e)}", exc_info=True)
            raise
