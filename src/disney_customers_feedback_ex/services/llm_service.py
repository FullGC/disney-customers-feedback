from __future__ import annotations

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """Service for querying the LLM with context."""
    
    def __init__(self) -> None:
        """Initialize the LLM service."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
        
    def query_with_context(
        self,
        question: str,
        reviews: list[dict[str, str]]
    ) -> str:
        """Query the LLM with question and review context.
        
        Args:
            question: The user's question.
            reviews: List of relevant review dictionaries.
            
        Returns:
            The LLM's answer based on the reviews.
        """
        # Build context from reviews
        context = self._build_context(reviews)
        
        logger.info(f"Querying LLM with {len(reviews)} reviews as context")
        
        # Create the prompt
        system_prompt = (
            "You are a helpful assistant that answers questions about Disney parks "
            "based on customer reviews. Use only the provided reviews to answer. "
            "If the reviews don't contain enough information, say so."
        )
        
        user_prompt = f"""Based on these customer reviews:

{context}

Question: {question}

Please provide a concise answer based on the reviews above."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content or ""
            logger.info("LLM response generated successfully")
            return answer
            
        except Exception as e:
            logger.error(f"Error querying LLM: {str(e)}")
            raise
            
    def _build_context(self, reviews: list[dict[str, str]]) -> str:
        """Build context string from reviews.
        
        Args:
            reviews: List of review dictionaries.
            
        Returns:
            Formatted context string.
        """
        if not reviews:
            return "No relevant reviews found."
            
        context_parts = []
        for i, review in enumerate(reviews, 1):
            context_parts.append(
                f"Review {i}:\n"
                f"Park: {review['branch']}\n"
                f"Rating: {review['rating']}\n"
                f"Date: {review['year_month']}\n"
                f"Reviewer Location: {review['reviewer_location']}\n"
                f"Review: {review['review_text']}\n"
            )
            
        return "\n---\n".join(context_parts)
