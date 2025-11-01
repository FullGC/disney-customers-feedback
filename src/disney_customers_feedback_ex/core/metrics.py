"""Custom metrics for monitoring the Disney Customer Feedback API."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

from opentelemetry import metrics

from disney_customers_feedback_ex.core.telemetry import get_meter

# Get meter for custom metrics
meter = get_meter(__name__)

# Request metrics
request_duration = meter.create_histogram(
    name="disney_api_request_duration_seconds",
    description="Request duration in seconds",
    unit="s"
)

request_count = meter.create_counter(
    name="disney_api_request_count",
    description="Total number of API requests",
    unit="1"
)

error_count = meter.create_counter(
    name="disney_api_error_count",
    description="Total number of errors",
    unit="1"
)

# Search metrics
search_type_count = meter.create_counter(
    name="disney_api_search_type_count",
    description="Count of searches by type (keyword/hybrid)",
    unit="1"
)

reviews_returned = meter.create_histogram(
    name="disney_api_reviews_returned",
    description="Number of reviews returned per query",
    unit="1"
)

# Component latency metrics
chromadb_search_duration = meter.create_histogram(
    name="disney_api_chromadb_search_duration_seconds",
    description="ChromaDB vector search duration",
    unit="s"
)

embedding_generation_duration = meter.create_histogram(
    name="disney_api_embedding_generation_duration_seconds",
    description="Embedding generation duration",
    unit="s"
)

llm_inference_duration = meter.create_histogram(
    name="disney_api_llm_inference_duration_seconds",
    description="LLM inference duration",
    unit="s"
)

keyword_search_duration = meter.create_histogram(
    name="disney_api_keyword_search_duration_seconds",
    description="Keyword search duration",
    unit="s"
)

# Filter usage metrics
filter_usage_count = meter.create_counter(
    name="disney_api_filter_usage_count",
    description="Count of filter usage by type",
    unit="1"
)

# Hybrid search strategy metrics
hybrid_strategy_count = meter.create_counter(
    name="disney_api_hybrid_strategy_count",
    description="Count of hybrid search strategy selection",
    unit="1"
)

candidate_count = meter.create_histogram(
    name="disney_api_candidate_count",
    description="Number of candidates from pandas filtering",
    unit="1"
)

# Cache metrics
cache_hit_count = meter.create_counter(
    name="disney_api_cache_hit_count",
    description="Total number of cache hits",
    unit="1"
)

cache_miss_count = meter.create_counter(
    name="disney_api_cache_miss_count",
    description="Total number of cache misses",
    unit="1"
)

cache_size = meter.create_gauge(
    name="disney_api_cache_size",
    description="Current number of entries in cache",
    unit="1"
)

cache_similarity_score = meter.create_histogram(
    name="disney_api_cache_similarity_score",
    description="Similarity score for cache hits",
    unit="1"
)

# Answer quality metrics
answer_length = meter.create_histogram(
    name="disney_api_answer_length",
    description="Length of generated answers in characters",
    unit="1"
)

reviews_used_count = meter.create_histogram(
    name="disney_api_reviews_used_count",
    description="Number of reviews used to generate answer",
    unit="1"
)

user_feedback_count = meter.create_counter(
    name="disney_api_user_feedback_count",
    description="Count of user feedback by rating",
    unit="1"
)

query_complexity_score = meter.create_histogram(
    name="disney_api_query_complexity_score",
    description="Estimated complexity of user query (0.0-1.0)",
    unit="1"
)

# Retrieval quality metrics
retrieval_precision = meter.create_histogram(
    name="disney_api_retrieval_precision",
    description="Precision of retrieved reviews (relevant/total)",
    unit="1"
)


@contextmanager
def measure_duration(histogram: metrics.Histogram, attributes: dict[str, str] | None = None) -> Generator[None, None, None]:
    """Context manager to measure duration and record to histogram.
    
    Args:
        histogram: The histogram to record duration to.
        attributes: Optional attributes to add to the measurement.
        
    Yields:
        None
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        histogram.record(duration, attributes=attributes or {})


def record_request(endpoint: str, method: str, status_code: int, duration: float) -> None:
    """Record API request metrics.
    
    Args:
        endpoint: The API endpoint.
        method: HTTP method.
        status_code: HTTP status code.
        duration: Request duration in seconds.
    """
    attributes = {
        "endpoint": endpoint,
        "method": method,
        "status_code": str(status_code)
    }
    
    request_count.add(1, attributes)
    request_duration.record(duration, attributes)
    
    # Record errors
    if status_code >= 400:
        error_count.add(1, attributes)


def record_search_type(search_type: str, has_filters: bool) -> None:
    """Record search type metrics.
    
    Args:
        search_type: Type of search (keyword, hybrid, semantic).
        has_filters: Whether filters were applied.
    """
    attributes = {
        "search_type": search_type,
        "has_filters": str(has_filters)
    }
    search_type_count.add(1, attributes)


def record_reviews_returned(count: int, search_type: str) -> None:
    """Record number of reviews returned.
    
    Args:
        count: Number of reviews returned.
        search_type: Type of search performed.
    """
    attributes = {"search_type": search_type}
    reviews_returned.record(count, attributes)


def record_filter_usage(filter_type: str) -> None:
    """Record filter usage.
    
    Args:
        filter_type: Type of filter (branch, location, both).
    """
    attributes = {"filter_type": filter_type}
    filter_usage_count.add(1, attributes)


def record_hybrid_strategy(strategy: str, candidate_count_value: int) -> None:
    """Record hybrid search strategy selection.
    
    Args:
        strategy: Strategy used (id_filtered, full_search).
        candidate_count_value: Number of candidates from pandas filtering.
    """
    strategy_attributes = {"strategy": strategy}
    hybrid_strategy_count.add(1, strategy_attributes)
    
    candidate_attributes = {"strategy": strategy}
    candidate_count.record(candidate_count_value, candidate_attributes)


def record_cache_hit(similarity_score: float | None = None) -> None:
    """Record cache hit metrics.
    
    Args:
        similarity_score: Optional similarity score for the cache hit.
    """
    cache_hit_count.add(1)
    if similarity_score is not None:
        cache_similarity_score.record(similarity_score)


def record_cache_miss() -> None:
    """Record cache miss metrics."""
    cache_miss_count.add(1)


def update_cache_size(size: int) -> None:
    """Update cache size gauge.
    
    Args:
        size: Current cache size.
    """
    cache_size.set(size)


def record_answer_quality(answer: str, num_reviews_used: int) -> None:
    """Record answer quality metrics.
    
    Args:
        answer: The generated answer text.
        num_reviews_used: Number of reviews used to generate the answer.
    """
    answer_length.record(len(answer))
    reviews_used_count.record(num_reviews_used)


def record_user_feedback(rating: str, question: str | None = None) -> None:
    """Record user feedback on answers.
    
    Args:
        rating: User rating (thumbs_up, thumbs_down).
        question: Optional question text for context.
    """
    attributes = {"rating": rating}
    user_feedback_count.add(1, attributes)


def record_query_complexity(complexity: float, query_type: str) -> None:
    """Record estimated query complexity.
    
    Args:
        complexity: Complexity score (0.0 = simple, 1.0 = complex).
        query_type: Type of query (simple, medium, complex).
    """
    attributes = {"query_type": query_type}
    query_complexity_score.record(complexity, attributes)


def record_retrieval_precision(precision: float, search_type: str) -> None:
    """Record retrieval precision metric.
    
    Args:
        precision: Precision score (relevant_reviews / total_reviews).
        search_type: Type of search performed.
    """
    attributes = {"search_type": search_type}
    retrieval_precision.record(precision, attributes)
