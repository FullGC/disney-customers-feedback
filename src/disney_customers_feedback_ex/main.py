from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel

from disney_customers_feedback_ex.core.lifespan import (
    lifespan,
    get_review_service,
    get_llm_service,
    get_cache_service,
    get_embedding_service,
    get_vector_store,
)
from disney_customers_feedback_ex.core.telemetry import get_tracer
from disney_customers_feedback_ex.core import metrics as app_metrics

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Disney Customer Feedback API",
    description="API for managing Disney customer feedback and reviews",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint that returns a welcome message.
    
    Returns:
        JSONResponse with welcome message and API information.
    """
    logger.info("Root endpoint accessed")
    return JSONResponse(
        content={
            "message": "Welcome to Disney Customer Feedback API! 🏰",
            "status": "healthy",
            "version": "0.1.0"
        }
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.
    
    Returns:
        JSONResponse indicating the API health status.
    """
    logger.info("Health check endpoint accessed")
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "disney-customer-feedback-api"
        }
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Response with Prometheus metrics in text format.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/cache/stats")
async def cache_stats() -> JSONResponse:
    """Get cache statistics.
    
    Returns:
        JSONResponse with cache statistics.
    """
    cache_service = get_cache_service()
    if cache_service is None:
        raise HTTPException(status_code=503, detail="Cache service not initialized")
    
    stats = cache_service.get_stats()
    logger.info("Cache stats endpoint accessed")
    return JSONResponse(content=stats)


@app.post("/cache/clear")
async def clear_cache() -> JSONResponse:
    """Clear the query cache.
    
    Returns:
        JSONResponse indicating success.
    """
    cache_service = get_cache_service()
    if cache_service is None:
        raise HTTPException(status_code=503, detail="Cache service not initialized")
    
    cache_service.clear()
    logger.info("Cache cleared via API endpoint")
    return JSONResponse(content={"status": "success", "message": "Cache cleared"})


class QueryRequest(BaseModel):
    """Request model for LLM queries."""
    question: str


class QueryResponse(BaseModel):
    """Response model for LLM queries."""
    question: str
    answer: str
    num_reviews_used: int
    cached: bool = False


@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest, fastapi_request: Request) -> QueryResponse:
    """Query the LLM with a question about Disney parks using review data.
    
    Args:
        request: The query request containing the question.
        fastapi_request: FastAPI request object for tracing.
        
    Returns:
        QueryResponse with the question, answer, and number of reviews used.
    """
    start_time = time.time()
    tracer = get_tracer(__name__)
    
    # Get services
    try:
        review_service = get_review_service()
        llm_service = get_llm_service()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    cache_service = get_cache_service()
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    
    logger.info(f"Query endpoint accessed with question: {request.question}")
    
    with tracer.start_as_current_span("query_endpoint") as span:
        try:
            span.set_attribute("question", request.question)
            
            # Check cache first
            if cache_service:
                cached_result = cache_service.get(request.question)
                if cached_result:
                    logger.info(f"Cache hit for question: {request.question}")
                    span.set_attribute("cache_hit", True)
                    
                    # Record cache hit metrics
                    app_metrics.record_cache_hit(cached_result.get("cache_similarity"))
                    app_metrics.update_cache_size(len(cache_service.cache))
                    
                    duration = time.time() - start_time
                    app_metrics.record_request(
                        endpoint="/query",
                        method="POST",
                        status_code=200,
                        duration=duration
                    )
                    
                    return QueryResponse(
                        question=request.question,
                        answer=cached_result["answer"],
                        num_reviews_used=cached_result["num_reviews_used"],
                        cached=True
                    )
                else:
                    logger.info(f"Cache miss for question: {request.question}")
                    span.set_attribute("cache_hit", False)
                    
                    # Record cache miss metrics
                    app_metrics.record_cache_miss()
                    app_metrics.update_cache_size(len(cache_service.cache))
            
            # Extract potential filters from the question (simple keyword matching)
            branch = None
            location = None
            
            # Simple branch detection
            if "hong kong" in request.question.lower():
                branch = "Hong_Kong"
            elif "california" in request.question.lower():
                branch = "California"
            elif "paris" in request.question.lower():
                branch = "Paris"
                
            # Simple location detection
            if "australia" in request.question.lower():
                location = "Australia"
            
            # Record filter usage
            has_filters = branch is not None or location is not None
            if has_filters:
                if branch and location:
                    app_metrics.record_filter_usage("both")
                elif branch:
                    app_metrics.record_filter_usage("branch")
                else:
                    app_metrics.record_filter_usage("location")
            
            span.set_attribute("has_branch_filter", branch is not None)
            span.set_attribute("has_location_filter", location is not None)
            
            # Search for relevant reviews using hybrid search if available
            search_type = "hybrid" if (embedding_service and vector_store) else "keyword"
            app_metrics.record_search_type(search_type, has_filters)
            
            with tracer.start_as_current_span("search_reviews") as search_span:
                search_span.set_attribute("search_type", search_type)
                
                if embedding_service and vector_store:
                    reviews = review_service.search_reviews_hybrid(
                        query=request.question,
                        branch=branch,
                        location=location,
                        max_results=10
                    )
                else:
                    reviews = review_service.search_reviews(
                        query=request.question,
                        branch=branch,
                        location=location,
                        max_results=10
                    )
                
                search_span.set_attribute("num_reviews", len(reviews))
                app_metrics.record_reviews_returned(len(reviews), search_type)
            
            # Query LLM with context
            with tracer.start_as_current_span("llm_query") as llm_span:
                llm_span.set_attribute("num_reviews_context", len(reviews))
                
                with app_metrics.measure_duration(
                    app_metrics.llm_inference_duration,
                    {"model": "gpt-4o-mini"}
                ):
                    answer = llm_service.query_with_context(request.question, reviews)
                
                llm_span.set_attribute("answer_length", len(answer))
            
            logger.info(f"Successfully generated answer using {len(reviews)} reviews")
            
            # Store in cache
            if cache_service:
                cache_service.set(request.question, answer, len(reviews))
                app_metrics.update_cache_size(len(cache_service.cache))
                logger.info(f"Stored answer in cache for question: {request.question}")
            
            # Record request metrics
            duration = time.time() - start_time
            app_metrics.record_request(
                endpoint="/query",
                method="POST",
                status_code=200,
                duration=duration
            )
            
            return QueryResponse(
                question=request.question,
                answer=answer,
                num_reviews_used=len(reviews),
                cached=False
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error processing query: {str(e)}")
            
            # Record error metrics
            app_metrics.record_request(
                endpoint="/query",
                method="POST",
                status_code=500,
                duration=duration
            )
            
            span.set_attribute("error", True)
            span.set_attribute("error_message", str(e))
            
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "disney_customers_feedback_ex.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )