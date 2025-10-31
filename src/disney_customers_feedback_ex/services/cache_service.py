"""Query caching service using Redis for semantic similarity-based caching."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import redis
from redis.exceptions import RedisError

from disney_customers_feedback_ex.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached query-answer pair with metadata."""
    
    def __init__(
        self,
        question: str,
        answer: str,
        embedding: list[float] | np.ndarray,
        num_reviews_used: int,
        timestamp: datetime | None = None
    ):
        """Initialize cache entry.
        
        Args:
            question: The original question.
            answer: The answer generated.
            embedding: The question embedding vector.
            num_reviews_used: Number of reviews used to generate the answer.
            timestamp: When the entry was created (defaults to now).
        """
        self.question = question
        self.answer = answer
        self.embedding = np.array(embedding, dtype=np.float32) if isinstance(embedding, list) else embedding
        self.num_reviews_used = num_reviews_used
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the cache entry.
        """
        return {
            "question": self.question,
            "answer": self.answer,
            "embedding": self.embedding.tolist(),
            "num_reviews_used": self.num_reviews_used,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary.
        
        Args:
            data: Dictionary representation.
            
        Returns:
            CacheEntry instance.
        """
        return cls(
            question=data["question"],
            answer=data["answer"],
            embedding=data["embedding"],
            num_reviews_used=data["num_reviews_used"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class QueryCacheService:
    """Service for caching query results using Redis with semantic similarity matching."""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24
    ):
        """Initialize the cache service.
        
        Args:
            embedding_service: Service for generating embeddings.
            redis_host: Redis server host.
            redis_port: Redis server port.
            redis_db: Redis database number.
            similarity_threshold: Minimum similarity score (0-1) for cache hit.
            ttl_hours: Time-to-live for cache entries in hours.
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = int(ttl_hours * 3600)
        
        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # We'll handle encoding/decoding manually
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        
        # Key prefixes
        self.cache_key_prefix = "disney_cache:"
        self.embedding_key_prefix = "disney_embedding:"
        self.all_keys_set = "disney_cache_keys"
    
    def _get_cache_key(self, identifier: str) -> str:
        """Generate cache key for a given identifier.
        
        Args:
            identifier: Unique identifier for the cache entry.
            
        Returns:
            Redis key for the cache entry.
        """
        return f"{self.cache_key_prefix}{identifier}"
    
    def _get_embedding_key(self, identifier: str) -> str:
        """Generate embedding key for a given identifier.
        
        Args:
            identifier: Unique identifier for the embedding.
            
        Returns:
            Redis key for the embedding.
        """
        return f"{self.embedding_key_prefix}{identifier}"
    
    def _compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.
            
        Returns:
            Cosine similarity score (0-1).
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def get(self, question: str) -> dict[str, Any] | None:
        """Retrieve cached answer for a similar question.
        
        Args:
            question: The question to look up.
            
        Returns:
            Dictionary with cached answer and metadata, or None if no match found.
        """
        try:
            # Generate embedding for the question
            query_embedding_list = self.embedding_service.embed_text(question)
            query_embedding = np.array(query_embedding_list, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to generate embedding for cache lookup: {str(e)}")
            return None
        
        try:
            # Get all cache keys
            cache_keys = self.redis_client.smembers(self.all_keys_set)
            
            if not cache_keys:
                logger.debug("Cache is empty")
                return None
            
            # Find most similar cached question
            best_similarity = 0.0
            best_match_key = None
            
            for key in cache_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                # Get embedding for this cached entry
                embedding_key = self._get_embedding_key(key_str)
                embedding_data = self.redis_client.get(embedding_key)
                
                if not embedding_data:
                    continue
                
                cached_embedding = np.array(json.loads(embedding_data), dtype=np.float32)
                similarity = self._compute_similarity(query_embedding, cached_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_key = key_str
            
            # Check if similarity meets threshold
            if best_match_key and best_similarity >= self.similarity_threshold:
                cache_key = self._get_cache_key(best_match_key)
                cached_data = self.redis_client.get(cache_key)
                
                if cached_data:
                    entry_dict = json.loads(cached_data)
                    logger.info(
                        f"Cache HIT - similarity: {best_similarity:.4f}, "
                        f"original: '{entry_dict['question']}', query: '{question}'"
                    )
                    return {
                        "question": question,
                        "answer": entry_dict["answer"],
                        "num_reviews_used": entry_dict["num_reviews_used"],
                        "cached": True,
                        "cache_similarity": best_similarity,
                        "original_question": entry_dict["question"]
                    }
            
            logger.debug(f"Cache MISS - best similarity: {best_similarity:.4f}, threshold: {self.similarity_threshold}")
            return None
            
        except RedisError as e:
            logger.error(f"Redis error during cache lookup: {str(e)}")
            return None
    
    def set(self, question: str, answer: str, num_reviews_used: int) -> None:
        """Store a question-answer pair in the cache.
        
        Args:
            question: The question asked.
            answer: The answer generated.
            num_reviews_used: Number of reviews used to generate the answer.
        """
        try:
            # Generate embedding for the question
            embedding = self.embedding_service.embed_text(question)
            
            # Create cache entry
            entry = CacheEntry(
                question=question,
                answer=answer,
                embedding=embedding,
                num_reviews_used=num_reviews_used
            )
            
            # Use a hash of the question as the identifier
            import hashlib
            identifier = hashlib.sha256(question.encode()).hexdigest()[:16]
            
            # Store cache entry
            cache_key = self._get_cache_key(identifier)
            entry_data = {
                "question": entry.question,
                "answer": entry.answer,
                "num_reviews_used": entry.num_reviews_used,
                "timestamp": entry.timestamp.isoformat()
            }
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(entry_data)
            )
            
            # Store embedding separately (also with TTL)
            embedding_key = self._get_embedding_key(identifier)
            self.redis_client.setex(
                embedding_key,
                self.ttl_seconds,
                json.dumps(entry.embedding.tolist())
            )
            
            # Add to set of all keys
            self.redis_client.sadd(self.all_keys_set, identifier)
            
            logger.info(f"Added to cache: '{question}' (key: {identifier})")
            
        except RedisError as e:
            logger.error(f"Redis error during cache set: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to add to cache: {str(e)}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            # Get all cache keys
            cache_keys = self.redis_client.smembers(self.all_keys_set)
            
            if cache_keys:
                # Delete all cache entries and embeddings
                for key in cache_keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    self.redis_client.delete(self._get_cache_key(key_str))
                    self.redis_client.delete(self._get_embedding_key(key_str))
                
                # Clear the set of all keys
                self.redis_client.delete(self.all_keys_set)
                
                logger.info(f"Cleared {len(cache_keys)} cache entries")
            else:
                logger.info("Cache was already empty")
                
        except RedisError as e:
            logger.error(f"Redis error during cache clear: {str(e)}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics.
        """
        try:
            # Get all cache keys
            cache_keys = self.redis_client.smembers(self.all_keys_set)
            total_entries = len(cache_keys)
            
            # Get memory info
            info = self.redis_client.info('memory')
            used_memory_human = info.get('used_memory_human', 'N/A')
            
            # Calculate oldest and newest entries
            oldest_entry = None
            newest_entry = None
            
            if cache_keys:
                timestamps = []
                for key in cache_keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    cache_key = self._get_cache_key(key_str)
                    cached_data = self.redis_client.get(cache_key)
                    
                    if cached_data:
                        entry_dict = json.loads(cached_data)
                        timestamps.append(datetime.fromisoformat(entry_dict['timestamp']))
                
                if timestamps:
                    oldest_entry = min(timestamps).isoformat()
                    newest_entry = max(timestamps).isoformat()
            
            return {
                "total_entries": total_entries,
                "similarity_threshold": self.similarity_threshold,
                "ttl_hours": self.ttl_seconds / 3600,
                "oldest_entry": oldest_entry,
                "newest_entry": newest_entry,
                "redis_memory_used": used_memory_human,
                "redis_host": self.redis_client.connection_pool.connection_kwargs.get('host'),
                "redis_port": self.redis_client.connection_pool.connection_kwargs.get('port')
            }
            
        except RedisError as e:
            logger.error(f"Redis error during get_stats: {str(e)}")
            return {
                "total_entries": 0,
                "error": str(e)
            }
    
    @property
    def cache(self) -> list[Any]:
        """Get all cache entries (for compatibility with metrics).
        
        Returns:
            List representation of cache size.
        """
        try:
            cache_keys = self.redis_client.smembers(self.all_keys_set)
            # Return a list with the right length for metrics
            return [None] * len(cache_keys)
        except RedisError:
            return []
