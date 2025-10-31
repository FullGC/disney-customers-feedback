from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from disney_customers_feedback_ex.services.embedding_service import EmbeddingService
from disney_customers_feedback_ex.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for loading and querying Disney customer reviews."""
    
    def __init__(
        self,
        data_path: Path,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None
    ) -> None:
        """Initialize the review service with data.
        
        Args:
            data_path: Path to the reviews CSV file.
            embedding_service: Optional embedding service for semantic search.
            vector_store: Optional vector store for semantic search.
        """
        self.data_path = data_path
        self.reviews_df: pd.DataFrame | None = None
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self._embeddings_indexed = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing special characters and converting to lowercase.
        
        Args:
            text: Text to normalize.
            
        Returns:
            Normalized text.
        """
        return text.lower().replace('_', '').replace('-', '').replace(' ', '')
        
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
        
    def index_embeddings(self) -> None:
        """Generate and index embeddings for all reviews."""
        if self.reviews_df is None:
            raise ValueError("Reviews not loaded. Call load_reviews() first.")
            
        if self.embedding_service is None or self.vector_store is None:
            logger.info("Embedding service or vector store not available, skipping embedding indexing")
            return
            
        if self._embeddings_indexed:
            logger.info("Embeddings already indexed")
            return
            
        try:
            logger.info("Starting embedding indexing process")
            total_reviews = len(self.reviews_df)
            
            # Check ChromaDB collection exists and get current count
            try:
                current_count = self.vector_store.collection.count()
                
                if current_count >= total_reviews:
                    logger.info(f"Vector store already contains {current_count} documents (need {total_reviews}), skipping indexing")
                    self._embeddings_indexed = True
                    return
                elif current_count > 0:
                    logger.warning(f"Vector store contains {current_count} documents but need {total_reviews}. This may cause duplicate indexing. Consider clearing the collection first.")
                    
            except Exception as e:
                logger.info(f"Could not check existing documents: {e}, proceeding with indexing")
            
            # Use batch size of 3000 for embedding generation and ChromaDB
            # This balances performance and memory usage
            batch_size = 3000
            
            logger.info(f"Processing {total_reviews} reviews in batches of {batch_size}")
            
            for batch_start in range(0, total_reviews, batch_size):
                batch_end = min(batch_start + batch_size, total_reviews)
                batch_df = self.reviews_df.iloc[batch_start:batch_end]
                
                logger.info(f"Processing batch {batch_start//batch_size + 1}/{(total_reviews + batch_size - 1)//batch_size} (rows {batch_start}-{batch_end-1})")
                
                # Prepare batch data
                batch_texts = batch_df['Review_Text'].fillna('No content').tolist()
                batch_ids = [str(batch_start + i) for i in range(len(batch_texts))]
                
                # Generate embeddings for this batch
                logger.info(f"Generating embeddings for {len(batch_texts)} reviews...")
                batch_embeddings = self.embedding_service.embed_batch(batch_texts)
                
                # Prepare metadata for this batch
                batch_metadata = []
                for _, row in batch_df.iterrows():
                    batch_metadata.append({
                        'branch': str(row.get('Branch', '')),
                        'rating': str(row.get('Rating', '')),
                        'year_month': str(row.get('Year_Month', '')),
                        'reviewer_location': str(row.get('Reviewer_Location', '')),
                        'review_text': str(row.get('Review_Text', ''))[:500]
                    })
                
                # Add batch to vector store
                logger.info(f"Adding batch to vector store...")
                self.vector_store.add_reviews_batch(
                    ids=batch_ids,
                    reviews_data=batch_metadata,
                    embeddings=batch_embeddings,
                    documents=batch_texts
                )
                
                logger.info(f"Successfully processed batch {batch_start//batch_size + 1}")
            
            self._embeddings_indexed = True
            logger.info(f"Successfully indexed {total_reviews} review embeddings")
            
        except Exception as e:
            logger.error(f"Failed to index embeddings: {str(e)}. Continuing with keyword search only.")
            # Don't re-raise, let the service continue with keyword search only
        
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
        # Use the shared filtering method
        df = self._apply_filters(branch, location)
        
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
        
    def search_reviews_hybrid(
        self,
        query: str,
        branch: str | None = None,
        location: str | None = None,
        max_results: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> list[dict[str, Any]]:
        """Search for relevant reviews using hybrid keyword + semantic search.
        
        Args:
            query: The search query text.
            branch: Optional Disney park branch to filter by.
            location: Optional reviewer location to filter by.
            max_results: Maximum number of results to return.
            keyword_weight: Weight for keyword search results.
            semantic_weight: Weight for semantic search results.
            
        Returns:
            List of relevant review dictionaries with combined scores.
        """
        # If vector search is not available, return keyword results only
        if self.embedding_service is None or self.vector_store is None or not self._embeddings_indexed:
            logger.info("Vector search not available, returning keyword results only")
            keyword_results = self.search_reviews(query, branch, location, max_results)
            return keyword_results
        
        logger.info(f"Performing hybrid search for query: {query}")
        
        # Step 1: Fast pandas filtering to get candidates
        df = self._apply_filters(branch, location)
        
        if df.empty:
            logger.info("No reviews match the filters")
            return []
        
        logger.info(f"Pandas filtering found {len(df)} candidate reviews")
        
        # Step 2: Keyword relevance scoring on candidates
        keyword_scores = self._calculate_keyword_scores(df, query)
        
        # Step 3: Semantic search strategy based on candidate count
        semantic_scores = {}
        
        try:
            # Generate query embedding once
            query_embedding = self.embedding_service.embed_text(query)
            
            # Decision: Use ID filtering if we have enough candidates to still get good results
            # We need at least 5x max_results candidates to ensure diversity after semantic filtering
            min_candidates_threshold = max_results * 5
            
            if len(df) >= min_candidates_threshold:
                # Strategy A: Search with ID filtering (more efficient)
                logger.info(f"Using ID-filtered search with {len(df)} candidates (>= {min_candidates_threshold} threshold)")
                
                candidate_ids = [str(idx) for idx in df.index]
                
                # Use ChromaDB's ids parameter to search within specific IDs
                semantic_results = self.vector_store.search_similar(
                    query_embedding=query_embedding,
                    n_results=min(len(candidate_ids), max_results * 2),
                    ids=candidate_ids
                )
                
            else:
                # Strategy B: Full search without ID filtering (better coverage)
                logger.info(f"Using full search without ID filtering (only {len(df)} candidates < {min_candidates_threshold} threshold)")
                
                semantic_results = self.vector_store.search_similar(
                    query_embedding=query_embedding,
                    n_results=max_results * 3  # Get more to allow for filtering
                )
                
                # Post-filter to only include reviews that match our pandas filters
                candidate_indices = set(df.index)
                semantic_results = [
                    result for result in semantic_results 
                    if int(result['id']) in candidate_indices
                ]
            
            # Convert semantic results to scores
            for result in semantic_results:
                doc_id = int(result['id'])
                semantic_scores[doc_id] = result['similarity_score']
            
            logger.info(f"Semantic search found {len(semantic_scores)} scored reviews")
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {str(e)}, using keyword-only results")
        
        # Step 4: Combine scores
        final_scores = {}
        
        # Start with all keyword scores
        for doc_id, kw_score in keyword_scores.items():
            sem_score = semantic_scores.get(doc_id, 0.0)
            
            if sem_score > 0:
                # Both keyword and semantic scores available
                final_scores[doc_id] = (keyword_weight * kw_score) + (semantic_weight * sem_score)
            else:
                # Only keyword score available
                final_scores[doc_id] = keyword_weight * kw_score
        
        # Add purely semantic results (that might not have keyword matches)
        for doc_id, sem_score in semantic_scores.items():
            if doc_id not in final_scores:
                final_scores[doc_id] = semantic_weight * sem_score
        
        # Step 5: Get top results
        top_indices = sorted(final_scores.keys(), key=lambda x: final_scores[x], reverse=True)[:max_results]
        
        # Step 6: Format results
        results = []
        for idx in top_indices:
            row = df.loc[idx]
            results.append({
                'branch': str(row.get('Branch', '')),
                'rating': str(row.get('Rating', '')),
                'year_month': str(row.get('Year_Month', '')),
                'reviewer_location': str(row.get('Reviewer_Location', '')),
                'review_text': str(row.get('Review_Text', ''))[:500],
                'keyword_score': keyword_scores.get(idx, 0.0),
                'semantic_score': semantic_scores.get(idx, 0.0),
                'combined_score': final_scores[idx]
            })
        
        logger.info(f"Returning {len(results)} hybrid search results")
        return results
    
    def _apply_filters(self, branch: str | None = None, location: str | None = None) -> pd.DataFrame:
        """Apply branch and location filters to the reviews DataFrame.
        
        Args:
            branch: Optional branch name to filter by.
            location: Optional location to filter by.
            
        Returns:
            Filtered DataFrame.
        """
        if self.reviews_df is None:
            raise ValueError("Reviews not loaded. Call load_reviews() first.")
            
        df = self.reviews_df.copy()
        
        if branch:
            # Normalize both the filter value and the column values for comparison
            branch_normalized = self._normalize_text(branch)
            mask = df['Branch'].fillna('').astype(str).apply(self._normalize_text).str.contains(
                branch_normalized, case=False, na=False
            )
            df = df[mask]
        
        if location:
            # Normalize both the filter value and the column values for comparison
            location_normalized = self._normalize_text(location)
            mask = df['Reviewer_Location'].fillna('').astype(str).apply(self._normalize_text).str.contains(
                location_normalized, case=False, na=False
            )
            df = df[mask]
            
        return df
    
    def _calculate_keyword_scores(self, df: pd.DataFrame, query: str) -> dict[int, float]:
        """Calculate keyword relevance scores for the given DataFrame."""
        query_words = set(query.lower().split())
        scores = {}
        
        for idx, row in df.iterrows():
            review_text = str(row.get('Review_Text', '')).lower()
            review_words = set(review_text.split())
            
            # Calculate word overlap
            common_words = query_words.intersection(review_words)
            if len(query_words) > 0:
                overlap_score = len(common_words) / len(query_words)
            else:
                overlap_score = 0.0
            
            # Boost for exact phrase matches
            phrase_boost = 1.0
            if query.lower() in review_text:
                phrase_boost = 1.5
            
            scores[idx] = overlap_score * phrase_boost
        
        return scores
    
    def _combine_search_results(
        self,
        keyword_results: list[dict[str, Any]],
        semantic_results: list[dict[str, Any]],
        keyword_weight: float,
        semantic_weight: float,
        max_results: int
    ) -> list[dict[str, Any]]:
        """Combine keyword and semantic search results with weighted scoring.
        
        Args:
            keyword_results: Results from keyword search.
            semantic_results: Results from semantic search.
            keyword_weight: Weight for keyword scores.
            semantic_weight: Weight for semantic scores.
            max_results: Maximum number of results to return.
            
        Returns:
            Combined and ranked results.
        """
        # Create a dictionary to track unique reviews and their scores
        review_scores = {}
        
        # Add keyword results with normalized scores
        for i, result in enumerate(keyword_results):
            review_text = result['review_text']
            keyword_score = 1.0 - (i / len(keyword_results))  # Higher rank = higher score
            
            if review_text not in review_scores:
                review_scores[review_text] = {
                    'result': result,
                    'keyword_score': keyword_score,
                    'semantic_score': 0.0
                }
            else:
                review_scores[review_text]['keyword_score'] = max(
                    review_scores[review_text]['keyword_score'],
                    keyword_score
                )
                
        # Add semantic results with their similarity scores
        for result in semantic_results:
            review_text = result['review_text']
            semantic_score = result.get('semantic_score', 0.0)
            
            if review_text not in review_scores:
                review_scores[review_text] = {
                    'result': result,
                    'keyword_score': 0.0,
                    'semantic_score': semantic_score
                }
            else:
                review_scores[review_text]['semantic_score'] = max(
                    review_scores[review_text]['semantic_score'],
                    semantic_score
                )
                
        # Calculate combined scores and rank
        final_results = []
        for review_data in review_scores.values():
            combined_score = (
                keyword_weight * review_data['keyword_score'] +
                semantic_weight * review_data['semantic_score']
            )
            
            result = review_data['result'].copy()
            result['combined_score'] = combined_score
            final_results.append(result)
            
        # Sort by combined score and return top results
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)
        return final_results[:max_results]
