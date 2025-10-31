from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from disney_customers_feedback_ex.core.logging import setup_logging
from disney_customers_feedback_ex.services.llm_service import LLMService
from disney_customers_feedback_ex.services.review_service import ReviewService

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global services
review_service: ReviewService | None = None
llm_service: LLMService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global review_service, llm_service
    
    # Startup
    setup_logging()
    logger.info("Disney Customer Feedback API starting up...")
    
    # Initialize services
    data_path = Path(__file__).parent / "resources" / "DisneylandReviews.csv"
    review_service = ReviewService(data_path)
    review_service.load_reviews()
    
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


class QueryRequest(BaseModel):
    """Request model for LLM queries."""
    question: str


class QueryResponse(BaseModel):
    """Response model for LLM queries."""
    question: str
    answer: str
    num_reviews_used: int


@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest) -> QueryResponse:
    """Query the LLM with a question about Disney parks using review data.
    
    Args:
        request: The query request containing the question.
        
    Returns:
        QueryResponse with the question, answer, and number of reviews used.
    """
    if review_service is None or llm_service is None:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    logger.info(f"Query endpoint accessed with question: {request.question}")
    
    try:
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
        
        # Search for relevant reviews
        reviews = review_service.search_reviews(
            query=request.question,
            branch=branch,
            location=location,
            max_results=10
        )
        
        # Query LLM with context
        answer = llm_service.query_with_context(request.question, reviews)
        
        logger.info(f"Successfully generated answer using {len(reviews)} reviews")
        
        return QueryResponse(
            question=request.question,
            answer=answer,
            num_reviews_used=len(reviews)
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "disney_customers_feedback_ex.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )