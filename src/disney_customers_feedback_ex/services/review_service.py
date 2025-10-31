from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for loading and querying Disney customer reviews."""
    
    def __init__(self, data_path: Path) -> None:
        """Initialize the review service with data.
        
        Args:
            data_path: Path to the reviews CSV file.
        """
        self.data_path = data_path
        self.reviews_df: pd.DataFrame | None = None
        
    def load_reviews(self) -> None:
        """Load reviews from CSV file into memory."""
        logger.info(f"Loading reviews from {self.data_path}")
        
        # Try different encodings to handle Unicode issues
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                self.reviews_df = pd.read_csv(self.data_path, encoding=encoding)
                logger.info(f"Loaded {len(self.reviews_df)} reviews using {encoding} encoding")
                return
            except UnicodeDecodeError:
                logger.debug(f"Failed to load with {encoding} encoding, trying next...")
                continue
        
        # If all encodings fail, raise an error
        raise ValueError(f"Unable to read CSV file with any supported encoding")
        
    def search_reviews(
        self,
        query: str,
        branch: str | None = None,
        location: str | None = None,
        max_results: int = 10
    ) -> list[dict[str, str]]:
        """Search for relevant reviews based on query and filters.
        
        Args:
            query: The search query text.
            branch: Optional Disney park branch to filter by.
            location: Optional reviewer location to filter by.
            max_results: Maximum number of results to return.
            
        Returns:
            List of relevant review dictionaries.
        """
        if self.reviews_df is None:
            raise ValueError("Reviews not loaded. Call load_reviews() first.")
            
        df = self.reviews_df.copy()
        
        # Apply filters
        if branch:
            # Normalize branch names by removing special characters for comparison
            branch_normalized = branch.lower().replace('_', '').replace('-', '').replace(' ', '')
            df = df[df['Branch'].fillna('').str.lower().str.replace('_', '').str.replace('-', '').str.replace(' ', '').str.contains(branch_normalized, case=False, na=False)]
            
        if location:
            # Normalize location names by removing special characters for comparison
            location_normalized = location.lower().replace('_', '').replace('-', '').replace(' ', '')
            df = df[df['Reviewer_Location'].fillna('').str.lower().str.replace('_', '').str.replace('-', '').str.replace(' ', '').str.contains(location_normalized, case=False, na=False)]
        
        # Check if dataframe is empty after filtering
        if df.empty:
            logger.info(f"No reviews found matching filters for query: {query}")
            return []
        
        # Simple text search in review text
        query_lower = query.lower()
        df['relevance'] = df['Review_Text'].fillna('').str.lower().apply(
            lambda x: sum(word in x for word in query_lower.split())
        )
        
        # Sort by relevance and take top results
        top_reviews = df.nlargest(max_results, 'relevance')
        
        # Convert to list of dicts
        results = []
        for _, row in top_reviews.iterrows():
            results.append({
                'branch': str(row.get('Branch', '')),
                'rating': str(row.get('Rating', '')),
                'year_month': str(row.get('Year_Month', '')),
                'reviewer_location': str(row.get('Reviewer_Location', '')),
                'review_text': str(row.get('Review_Text', ''))[:500]  # Limit text length
            })
            
        logger.info(f"Found {len(results)} relevant reviews for query: {query}")
        return results
