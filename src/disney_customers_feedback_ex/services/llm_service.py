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
    
    def estimate_query_complexity(self, question: str) -> tuple[float, str]:
        """Estimate the complexity of a user query.
        
        Complexity is based on:
        - Question length
        - Number of clauses/entities
        - Comparative/analytical nature
        - Multiple filters/conditions
        
        Args:
            question: The user's question.
            
        Returns:
            Tuple of (complexity_score, complexity_type)
            - complexity_score: 0.0 (simple) to 1.0 (complex)
            - complexity_type: "simple", "medium", or "complex"
        """
        score = 0.0
        
        # Length factor (0-0.2)
        word_count = len(question.split())
        if word_count > 20:
            score += 0.2
        elif word_count > 10:
            score += 0.1
        
        # Comparative/analytical keywords (0-0.3)
        comparative_words = ["compare", "versus", "vs", "better", "worse", "difference", "similar"]
        analytical_words = ["why", "how", "analyze", "trend", "pattern", "correlation"]
        
        question_lower = question.lower()
        if any(word in question_lower for word in comparative_words):
            score += 0.2
        if any(word in question_lower for word in analytical_words):
            score += 0.3
        
        # Multiple entities/filters (0-0.3)
        branches = ["california", "hong kong", "paris"]
        branch_count = sum(1 for branch in branches if branch in question_lower)
        if branch_count > 1:
            score += 0.3
        elif branch_count == 1:
            score += 0.1
        
        # Question marks/multiple questions (0-0.2)
        question_marks = question.count("?")
        if question_marks > 1:
            score += 0.2
        
        # Determine complexity type
        if score < 0.3:
            complexity_type = "simple"
        elif score < 0.7:
            complexity_type = "medium"
        else:
            complexity_type = "complex"
        
        return min(score, 1.0), complexity_type
        
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
