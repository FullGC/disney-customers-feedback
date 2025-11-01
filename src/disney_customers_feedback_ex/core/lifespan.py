"""Application lifespan management."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from disney_customers_feedback_ex.core.logging import setup_logging
from disney_customers_feedback_ex.core.telemetry import setup_telemetry
from disney_customers_feedback_ex.services.embedding_service import EmbeddingService
from disney_customers_feedback_ex.services.llm_service import LLMService
from disney_customers_feedback_ex.services.review_service import ReviewService
from disney_customers_feedback_ex.services.vector_store import VectorStore
from disney_customers_feedback_ex.services.cache_service import QueryCacheService

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global services
review_service: ReviewService | None = None
llm_service: LLMService | None = None
embedding_service: EmbeddingService | None = None
vector_store: VectorStore | None = None
cache_service: QueryCacheService | None = None


def get_review_service() -> ReviewService:
    """Get the review service instance.
    
    Returns:
        ReviewService instance.
        
    Raises:
        RuntimeError: If service not initialized.
    """
    if review_service is None:
        raise RuntimeError("Review service not initialized")
    return review_service


def get_llm_service() -> LLMService:
    """Get the LLM service instance.
    
    Returns:
        LLMService instance.
        
    Raises:
        RuntimeError: If service not initialized.
    """
    if llm_service is None:
        raise RuntimeError("LLM service not initialized")
    return llm_service


def get_cache_service() -> QueryCacheService | None:
    """Get the cache service instance.
    
    Returns:
        QueryCacheService instance or None if not initialized.
    """
    return cache_service


def get_embedding_service() -> EmbeddingService | None:
    """Get the embedding service instance.
    
    Returns:
        EmbeddingService instance or None if not initialized.
    """
    return embedding_service


def get_vector_store() -> VectorStore | None:
    """Get the vector store instance.
    
    Returns:
        VectorStore instance or None if not initialized.
    """
    return vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown of all services.
    
    Args:
        app: FastAPI application instance.
        
    Yields:
        None during application runtime.
    """
    global review_service, llm_service, embedding_service, vector_store, cache_service
    
    # ========== STARTUP ==========
    setup_logging()
    logger.info("🚀 Disney Customer Feedback API starting up...")
    
    # Setup telemetry
    setup_telemetry(app, "disney-customer-feedback-api")
    logger.info("📊 OpenTelemetry instrumentation enabled")
    
    # Get data path
    data_path = Path(__file__).parent.parent / "resources" / "DisneylandReviews.csv"
    
    # Initialize embedding service
    logger.info("🔤 Initializing embedding service...")
    embedding_service = EmbeddingService()
    embedding_service.load_model()
    logger.info("✅ Embedding service initialized")
    
    # Initialize cache service with Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    logger.info(f"💾 Initializing cache service with Redis at {redis_host}:{redis_port}...")
    try:
        cache_service = QueryCacheService(
            embedding_service=embedding_service,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=0,
            similarity_threshold=0.95,
            ttl_hours=24
        )
        logger.info("✅ Cache service initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Cache service initialization failed: {str(e)}. Continuing without caching.")
        cache_service = None
    
    # Initialize vector store
    logger.info("🗄️  Initializing vector store...")
    vector_store = VectorStore()
    try:
        vector_store.connect()
        vector_store.create_collection()
        logger.info("✅ Vector store connected and collection created successfully")
    except Exception as e:
        logger.warning(
            f"⚠️ Vector store connection failed: {str(e)}. "
            "Continuing without semantic search."
        )
        vector_store = None
        # Don't set embedding_service to None here as cache still needs it
    
    # Initialize review service
    logger.info("Initializing review service...")
    data_path = Path(__file__).parent.parent / "resources" / "DisneylandReviews.csv"
    review_service = ReviewService(
        data_path=data_path,
        embedding_service=embedding_service,
        vector_store=vector_store
    )
    
    # Load reviews from CSV
    logger.info("📖 Loading reviews from CSV...")
    review_service.load_reviews()
    num_reviews = len(review_service.reviews_df) if review_service.reviews_df is not None else 0
    logger.info(f"✅ Review service initialized with {num_reviews} reviews")
    
    # Index embeddings if vector store is available
    if vector_store and embedding_service:
        try:
            logger.info("🔍 Indexing embeddings in vector store...")
            review_service.index_embeddings()
            logger.info("✅ Embeddings indexed successfully")
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to index embeddings: {str(e)}. "
                "Continuing with keyword search only."
            )
    
    # Initialize LLM service
    logger.info("🤖 Initializing LLM service...")
    llm_service = LLMService()
    logger.info("✅ LLM service initialized")
    
    logger.info("✨ All services initialized successfully! Ready to serve requests.")
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("👋 Disney Customer Feedback API shutting down...")
    
    # Cleanup vector store connection if needed
    if vector_store:
        logger.info("Closing vector store connection...")
        # Add any cleanup code here if needed
    
    # Cleanup cache service connection if needed
    if cache_service:
        logger.info("Closing cache service connection...")
        # Add any cleanup code here if needed
    
    logger.info("✅ Shutdown complete. Goodbye!")
