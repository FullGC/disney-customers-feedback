from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

from disney_customers_feedback_ex.core.logging import setup_logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info("Disney Customer Feedback API starting up...")
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


@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest) -> QueryResponse:
    """Query the LLM with a question about Disney parks.
    
    Args:
        request: The query request containing the question.
        
    Returns:
        QueryResponse with the question and answer.
    """
    logger.info(f"Query endpoint accessed with question: {request.question}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions about Disney parks based on customer reviews."
                },
                {
                    "role": "user",
                    "content": request.question
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        logger.info(f"LLM response generated successfully")
        
        return QueryResponse(question=request.question, answer=answer)
        
    except Exception as e:
        logger.error(f"Error querying LLM: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "disney_customers_feedback_ex.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )