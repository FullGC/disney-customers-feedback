from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel

from disney_customers_feedback_ex.core.logging import setup_logging
from disney_customers_feedback_ex.core.telemetry import setup_telemetry, get_tracer
from disney_customers_feedback_ex.core import metrics as app_metrics
from disney_customers_feedback_ex.services.embedding_service import EmbeddingService
from disney_customers_feedback_ex.services.llm_service import LLMService
from disney_customers_feedback_ex.services.review_service import ReviewService
from disney_customers_feedback_ex.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global services
review_service: ReviewService | None = None
llm_service: LLMService | None = None
embedding_service: EmbeddingService | None = None
vector_store: VectorStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global review_service, llm_service, embedding_service, vector_store
    
    # Startup
    setup_logging()
    logger.info("Disney Customer Feedback API starting up...")
    
    # Setup telemetry
    setup_telemetry(app, "disney-customer-feedback-api")
    logger.info("OpenTelemetry instrumentation enabled")
    
    # Initialize services
    data_path = Path(__file__).parent / "resources" / "DisneylandReviews.csv"
    
    # Initialize embedding service
    embedding_service = EmbeddingService()
    embedding_service.load_model()
    
    # Initialize vector store
    vector_store = VectorStore()
    try:
        vector_store.connect()
        
        # Clean the database before loading new data
        # logger.info("Cleaning ChromaDB collection before loading new data...")
        #vector_store.reset_collection()
        vector_store.create_collection()
        logger.info("Vector store connected and cleaned successfully")
    except Exception as e:
        logger.warning(f"Vector store connection failed: {str(e)}. Continuing without semantic search.")
        vector_store = None
        embedding_service = None
    
    # Initialize review service with optional vector components
    review_service = ReviewService(data_path, embedding_service, vector_store)
    review_service.load_reviews()
    
    # Index embeddings if vector store is available
    if vector_store and embedding_service:
        try:
            review_service.index_embeddings()
        except Exception as e:
            logger.warning(f"Failed to index embeddings: {str(e)}. Continuing with keyword search only.")
    
    # Initialize LLM service
    llm_service = LLMService()
    
    yield
    
    # Shutdown
    logger.info("Disney Customer Feedback API shutting down...")


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


class QueryRequest(BaseModel):
    """Request model for LLM queries."""
    question: str


class QueryResponse(BaseModel):
    """Response model for LLM queries."""
    question: str
    answer: str
    num_reviews_used: int


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
    
    if review_service is None or llm_service is None:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    logger.info(f"Query endpoint accessed with question: {request.question}")
    
    with tracer.start_as_current_span("query_endpoint") as span:
        try:
            span.set_attribute("question", request.question)
            
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
                num_reviews_used=len(reviews)
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