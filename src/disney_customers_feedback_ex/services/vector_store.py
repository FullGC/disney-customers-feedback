from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Service for storing and querying vectors using ChromaDB."""
    
    def __init__(self, host: str = "localhost", port: int = 8001) -> None:
        """Initialize the vector store.
        
        Args:
            host: ChromaDB server host.
            port: ChromaDB server port.
        """
        self.host = host
        self.port = port
        self.client: chromadb.HttpClient | None = None
        self.collection: chromadb.Collection | None = None
        
    def connect(self) -> None:
        """Connect to ChromaDB server."""
        logger.info(f"Connecting to ChromaDB at {self.host}:{self.port}")
        self.client = chromadb.HttpClient(
            host=self.host,
            port=self.port,
            settings=Settings(allow_reset=True)
        )
        logger.info("Connected to ChromaDB successfully")
        
    def create_collection(self, name: str = "disney_reviews") -> None:
        """Create or get a collection for Disney reviews.
        
        Args:
            name: Name of the collection.
        """
        if self.client is None:
            raise ValueError("Client not connected. Call connect() first.")
            
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name)
            logger.info(f"Retrieved existing collection: {name}")
        except Exception:
            # Create new collection if it doesn't exist
            self.collection = self.client.create_collection(
                name=name,
                metadata={"description": "Disney customer reviews with embeddings"}
            )
            logger.info(f"Created new collection: {name}")
            
    def add_reviews_batch(
        self,
        ids: list[str],
        reviews_data: list[dict[str, str]],
        embeddings: list[list[float]],
        documents: list[str]
    ) -> None:
        """Add a batch of reviews with embeddings to the vector store.
        
        Args:
            ids: List of unique IDs for the reviews.
            reviews_data: List of review metadata dictionaries.
            embeddings: List of embedding vectors.
            documents: List of review text documents.
        """
        if self.collection is None:
            raise ValueError("Collection not created. Call create_collection() first.")
            
        try:
            logger.info(f"Adding batch of {len(ids)} reviews to ChromaDB")
            
            # Ensure all lists have the same length
            if not (len(ids) == len(reviews_data) == len(embeddings) == len(documents)):
                raise ValueError("All input lists must have the same length")
            
            # ChromaDB add method
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=reviews_data,
                embeddings=embeddings
            )
            
            logger.info(f"Successfully added {len(ids)} reviews to vector store")
            
        except Exception as e:
            logger.error(f"Error adding batch to vector store: {str(e)}")
            raise

    def add_reviews(
        self,
        reviews: list[dict[str, Any]],
        embeddings: list[list[float]]
    ) -> None:
        """Add reviews with embeddings to the collection.
        
        Args:
            reviews: List of review dictionaries.
            embeddings: List of embedding vectors.
        """
        # Generate IDs and documents from reviews_data
        ids = [f"review_{i}" for i in range(len(reviews))]
        documents = [review.get('review_text', '') for review in reviews]
        
        self.add_reviews_batch(
            ids=ids,
            reviews_data=reviews,
            embeddings=embeddings,
            documents=documents
        )
        
    def search_similar(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where_filter: dict | None = None,
        ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar documents in the vector store.
        
        Args:
            query_embedding: The query embedding vector.
            n_results: Maximum number of results to return.
            where_filter: Optional filter conditions for metadata.
            ids: Optional list of IDs to search within (subset filtering).
            
        Returns:
            List of similar documents with metadata and similarity scores.
        """
        try:
            if not self.collection:
                raise ValueError("Collection not initialized")
            
            # Build query parameters
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["metadatas", "documents", "distances"]
            }
            
            # Add where filter if provided
            if where_filter:
                query_params["where"] = where_filter
            
            # Add ids filter if provided
            if ids:
                query_params["ids"] = ids
                
            results = self.collection.query(**query_params)
            
            # Transform results to our expected format
            formatted_results = []
            for i in range(len(results['ids'][0])):
                similarity_score = 1.0 - results['distances'][0][i]  # Convert distance to similarity
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'review_text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': similarity_score
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            return []
    
    def get_collection_stats(self) -> dict[str, Any]:
        """Get detailed statistics about the collection.
        
        Returns:
            Dictionary with collection statistics.
        """
        if self.collection is None:
            return {"error": "Collection not initialized"}
            
        try:
            count = self.collection.count()
            
            # Get sample of documents to see data structure
            sample_data = self.collection.peek(limit=5)
            
            # Get unique values for key metadata fields
            all_metadata = self.collection.get(include=['metadatas'])['metadatas']
            
            branches = set()
            locations = set()
            ratings = set()
            
            for meta in all_metadata[:100]:  # Sample first 100 for performance
                if meta:
                    branches.add(meta.get('branch', 'N/A'))
                    locations.add(meta.get('reviewer_location', 'N/A'))
                    ratings.add(meta.get('rating', 'N/A'))
            
            return {
                "total_documents": count,
                "sample_ids": sample_data.get('ids', [])[:5],
                "sample_metadata": sample_data.get('metadatas', [])[:3],
                "unique_branches": sorted(list(branches))[:10],
                "unique_locations": sorted(list(locations))[:10], 
                "unique_ratings": sorted(list(ratings)),
                "collection_name": "disney_reviews"
            }
            
        except Exception as e:
            return {"error": f"Failed to get stats: {str(e)}"}
    
    def search_by_metadata(
        self,
        branch: str | None = None,
        location: str | None = None,
        rating: str | None = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search documents by metadata filters only.
        
        Args:
            branch: Filter by branch name.
            location: Filter by reviewer location.
            rating: Filter by rating.
            limit: Maximum number of results.
            
        Returns:
            List of matching documents with metadata.
        """
        if self.collection is None:
            return []
            
        try:
            # Build where clause
            where_clause = {}
            if branch:
                where_clause["branch"] = {"$eq": branch}
            if location:
                where_clause["reviewer_location"] = {"$eq": location}
            if rating:
                where_clause["rating"] = {"$eq": rating}
            
            results = self.collection.get(
                where=where_clause if where_clause else None,
                limit=limit,
                include=['documents', 'metadatas', 'ids']
            )
            
            # Format results
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i][:200] + "..." if len(results['documents'][i]) > 200 else results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching by metadata: {str(e)}")
            return []
    
    def get_sample_documents(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get a sample of documents from the collection.
        
        Args:
            limit: Number of documents to retrieve.
            
        Returns:
            List of sample documents with metadata.
        """
        if self.collection is None:
            return []
            
        try:
            results = self.collection.peek(limit=limit)
            
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i][:200] + "..." if len(results['documents'][i]) > 200 else results['documents'][i],
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting sample documents: {str(e)}")
            return []

    def reset_collection(self) -> None:
        """Reset (clear) the collection."""
        if self.client is None:
            raise ValueError("Client not connected. Call connect() first.")
            
        try:
            self.client.delete_collection("disney_reviews")
            logger.info("Collection deleted")
        except Exception:
            logger.info("Collection didn't exist, nothing to delete")
            
        self.create_collection()
        logger.info("Collection reset successfully")