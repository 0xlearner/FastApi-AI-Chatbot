import logging

from app.core.logging_config import get_logger


# Utility functions for getting loggers
def get_service_logger(service_name: str) -> logging.Logger:
    """Get a logger for a service"""
    return get_logger(f"app.services.{service_name}")


def get_api_logger(endpoint_name: str) -> logging.Logger:
    """Get a logger for an API endpoint"""
    return get_logger(f"app.api.{endpoint_name}")


def get_pipeline_logger(component_name: str) -> logging.Logger:
    """Get a logger for a RAG pipeline component"""
    return get_logger(f"app.services.rag_pipeline.{component_name}")
