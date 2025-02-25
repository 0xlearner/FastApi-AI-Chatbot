import time
from typing import Dict, List

import httpx
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from app.utils.logging import get_pipeline_logger

logger = get_pipeline_logger("llm")


class OllamaLLM:
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = 1200  # Increased timeout to 60 seconds
        logger.info(f"Initialized OllamaLLM with model: {model_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.ReadTimeout),
    )
    async def _make_llm_request(self, prompt: str) -> str:
        """Make request to Ollama with retry logic"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.debug(f"Sending request to Ollama API: {
                         self.base_url}/api/generate")
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_ctx": 4096,  # Increase context window
                    },
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_response(self, query: str, context: List[Dict]) -> str:
        """Generate a response using the LLM"""
        start_time = time.time()
        logger.info(f"Generating response for query: {query}")
        logger.debug(f"Context contains {len(context)} documents")

        try:
            # Format context more concisely
            context_text = "\n\n".join(
                [
                    f"[Page {doc['metadata']['page_number']}]: {doc['text']}"
                    for doc in sorted(
                        context, key=lambda x: x["metadata"]["score"], reverse=True
                    )
                ]
            )
            logger.debug(f"Formatted context length: {
                         len(context_text)} characters")

            # Create a more focused prompt
            prompt = f"""You are a helpful assistant answering questions about a document. Use the following context to answer the question.
            If the answer is not in the context, say "I cannot find information about that in the document."

            Context:
            {context_text}

            Question: {query}

            Answer (be concise and specific):"""

            logger.debug(f"Generated prompt with length: {
                         len(prompt)} characters")

            # Try to get response with retries
            try:
                response = await self._make_llm_request(prompt)
                processing_time = time.time() - start_time
                logger.info(f"Generated response in {
                            processing_time:.2f} seconds")
                return response
            except httpx.ReadTimeout:
                logger.warning("All retry attempts failed due to timeout")
                # Fall back to summarizing the most relevant context
                most_relevant = context[0] if context else None
                if most_relevant and most_relevant["metadata"]["score"] > 0.2:
                    return (
                        f"While I'm having trouble generating a complete response, "
                        f"I found relevant information on page {
                            most_relevant['metadata']['page_number']}. "
                        f"Here's the relevant excerpt:\n\n{
                            most_relevant['text']}"
                    )
                return (
                    "I found some potentially relevant information but am having trouble processing it. "
                    "Please try your question again, or try asking in a different way."
                )

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return (
                "I apologize, but I encountered an error while trying to generate a response. "
                "Please try again or rephrase your question."
            )
