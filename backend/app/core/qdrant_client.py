"""
Qdrant vector store client for semantic search
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class QdrantStore:
    """
    Qdrant vector store client for document embeddings

    Features:
    - Tenant-isolated vector search
    - Collection management
    - Point upsert/delete with metadata
    - Filtered similarity search
    """

    def __init__(self):
        """Initialize Qdrant client"""
        self._client: Optional[QdrantClient] = None
        self._initialized = False

    def _ensure_client(self) -> QdrantClient:
        """
        Ensure Qdrant client is initialized

        Returns:
            Qdrant client instance
        """
        if not self._client or not self._initialized:
            try:
                self._client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=30,
                )

                self._initialized = True
                logger.info(
                    "qdrant_client_initialized",
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                )

            except Exception as e:
                logger.error(
                    "qdrant_client_initialization_failed",
                    error=str(e),
                    host=settings.QDRANT_HOST,
                )
                raise Exception(f"Failed to initialize Qdrant client: {str(e)}")

        return self._client

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: Distance = Distance.COSINE,
    ) -> bool:
        """
        Create a Qdrant collection for embeddings

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of embedding vectors (default: 1536 for OpenAI)
            distance: Distance metric (COSINE, EUCLID, DOT)

        Returns:
            True if successful
        """
        try:
            client = self._ensure_client()

            # Check if collection already exists
            collections = client.get_collections().collections
            if any(c.name == collection_name for c in collections):
                logger.info(
                    "qdrant_collection_already_exists",
                    collection_name=collection_name,
                )
                return True

            # Create collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
            )

            logger.info(
                "qdrant_collection_created",
                collection_name=collection_name,
                vector_size=vector_size,
                distance=distance.value,
            )

            return True

        except Exception as e:
            logger.error(
                "qdrant_collection_creation_failed",
                collection_name=collection_name,
                error=str(e),
            )
            return False

    async def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        tenant_id: str,
    ) -> bool:
        """
        Upsert points (embeddings) to Qdrant with tenant metadata

        Args:
            collection_name: Target collection
            points: List of points with id, vector, payload
            tenant_id: Tenant UUID for isolation

        Returns:
            True if successful

        Example:
            points = [
                {
                    "id": "chunk-uuid-1",
                    "vector": [0.1, 0.2, ...],
                    "payload": {
                        "document_id": "doc-uuid",
                        "chunk_index": 0,
                        "content": "text...",
                        "metadata": {...}
                    }
                }
            ]
        """
        try:
            client = self._ensure_client()

            # Add tenant_id to all payloads for isolation
            qdrant_points = []
            for point in points:
                payload = point.get("payload", {})
                payload["tenant_id"] = tenant_id

                qdrant_points.append(
                    PointStruct(
                        id=str(point["id"]),
                        vector=point["vector"],
                        payload=payload,
                    )
                )

            # Upsert to Qdrant
            client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )

            logger.info(
                "qdrant_points_upserted",
                collection_name=collection_name,
                tenant_id=tenant_id,
                point_count=len(qdrant_points),
            )

            return True

        except Exception as e:
            logger.error(
                "qdrant_points_upsert_failed",
                collection_name=collection_name,
                tenant_id=tenant_id,
                error=str(e),
            )
            return False

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        tenant_id: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with tenant isolation

        Args:
            collection_name: Collection to search
            query_vector: Query embedding vector
            tenant_id: Tenant UUID for isolation
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Additional metadata filters

        Returns:
            List of search results with scores
        """
        try:
            client = self._ensure_client()

            # Build filter for tenant isolation
            must_conditions = [
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id),
                )
            ]

            # Add additional filters if provided
            if filter_conditions:
                for key, value in filter_conditions.items():
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )

            search_filter = Filter(must=must_conditions)

            # Perform search
            search_results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                })

            logger.info(
                "qdrant_search_completed",
                collection_name=collection_name,
                tenant_id=tenant_id,
                result_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "qdrant_search_failed",
                collection_name=collection_name,
                tenant_id=tenant_id,
                error=str(e),
            )
            return []

    async def delete_points(
        self,
        collection_name: str,
        point_ids: List[str],
        tenant_id: str,
    ) -> bool:
        """
        Delete specific points from collection

        Args:
            collection_name: Collection name
            point_ids: List of point IDs to delete
            tenant_id: Tenant UUID for logging

        Returns:
            True if successful
        """
        try:
            client = self._ensure_client()

            client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
            )

            logger.info(
                "qdrant_points_deleted",
                collection_name=collection_name,
                tenant_id=tenant_id,
                deleted_count=len(point_ids),
            )

            return True

        except Exception as e:
            logger.error(
                "qdrant_points_deletion_failed",
                collection_name=collection_name,
                tenant_id=tenant_id,
                error=str(e),
            )
            return False

    async def delete_by_filter(
        self,
        collection_name: str,
        tenant_id: str,
        document_id: Optional[str] = None,
    ) -> bool:
        """
        Delete points by filter (e.g., all chunks of a document)

        Args:
            collection_name: Collection name
            tenant_id: Tenant UUID
            document_id: Optional document ID to delete all its chunks

        Returns:
            True if successful
        """
        try:
            client = self._ensure_client()

            # Build filter
            must_conditions = [
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id),
                )
            ]

            if document_id:
                must_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                )

            delete_filter = Filter(must=must_conditions)

            # Delete by filter
            client.delete(
                collection_name=collection_name,
                points_selector=delete_filter,
            )

            logger.info(
                "qdrant_points_deleted_by_filter",
                collection_name=collection_name,
                tenant_id=tenant_id,
                document_id=document_id,
            )

            return True

        except Exception as e:
            logger.error(
                "qdrant_delete_by_filter_failed",
                collection_name=collection_name,
                tenant_id=tenant_id,
                error=str(e),
            )
            return False


# Global Qdrant client instance
qdrant_store = QdrantStore()
