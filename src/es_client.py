"""
Elasticsearch client for MOI Elasticsearch NLP Query System

Handles all Elasticsearch operations: connection, health checks, mapping retrieval, query execution.
Follows constitution principles: modular architecture, error handling, integration testing.
"""

from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError, RequestError


class ESClient:
    """
    Elasticsearch client wrapper.

    Provides clean interface for:
    - Connection management
    - Cluster health checks
    - Index mapping retrieval
    - Query DSL execution

    Following constitution: Module exposes public methods only, handles connection failures gracefully
    """

    def __init__(self, config):
        """
        Initialize Elasticsearch client.

        Args:
            config: Config instance with ES connection details

        Following constitution: Connection pooling with singleton pattern
        """
        self.config = config
        self._client: Optional[Elasticsearch] = None

    def connect(self) -> Elasticsearch:
        """
        Establish connection to Elasticsearch cluster.

        Returns:
            Elasticsearch: Connected client instance

        Raises:
            ConnectionError: If connection fails

        Following constitution: Explicit timeout (5s per constitution)
        """
        if self._client is None:
            try:
                self._client = Elasticsearch(
                    [f'http://{self.config.ES_HOST}:{self.config.ES_PORT}'],
                    basic_auth=(self.config.ES_USER, self.config.ES_PASSWORD),
                    request_timeout=5,  # 5 second timeout per constitution
                    max_retries=1,
                    retry_on_timeout=True
                )

                # Verify connection
                if not self._client.ping():
                    raise ConnectionError("Failed to ping Elasticsearch cluster")

            except Exception as e:
                raise ConnectionError(f"Failed to connect to Elasticsearch at {self.config.ES_HOST}:{self.config.ES_PORT}: {str(e)}")

        return self._client

    def check_health(self) -> Dict[str, Any]:
        """
        Check Elasticsearch cluster health.

        Returns:
            dict: Cluster health information with status field

        Raises:
            ConnectionError: If cluster is unreachable

        Following constitution: Health check before accepting queries (FR-001)
        """
        client = self.connect()

        try:
            health = client.cluster.health()
            return health.body if hasattr(health, 'body') else health
        except Exception as e:
            raise ConnectionError(f"Failed to check cluster health: {str(e)}")

    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.

        Args:
            index_name: Name of the index to check

        Returns:
            bool: True if index exists, False otherwise
        """
        client = self.connect()

        try:
            return client.indices.exists(index=index_name).body
        except Exception:
            return False

    def get_mapping(self, index_name: str) -> Dict[str, Any]:
        """
        Retrieve index mapping for schema discovery.

        Args:
            index_name: Name of the index

        Returns:
            dict: Index mapping definition

        Raises:
            NotFoundError: If index doesn't exist
            ConnectionError: If request fails

        Following constitution: Index mapping retrieval (FR-004)
        """
        client = self.connect()

        try:
            mapping = client.indices.get_mapping(index=index_name)
            return mapping.body if hasattr(mapping, 'body') else mapping
        except NotFoundError as e:
            raise RuntimeError(f"Index '{index_name}' not found in Elasticsearch") from e
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve mapping for index '{index_name}': {str(e)}") from e

    def execute_query(self, index_name: str, query_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Query DSL against an index.

        Args:
            index_name: Target index name
            query_dsl: Elasticsearch Query DSL as dict

        Returns:
            dict: Query results with hits structure

        Raises:
            RequestError: If Query DSL is invalid
            ConnectionError: If execution fails

        Following constitution: Query execution (FR-008), <100ms p95 (constitution performance goal)
        """
        client = self.connect()

        try:
            response = client.search(index=index_name, body=query_dsl)
            return response.body if hasattr(response, 'body') else response
        except RequestError as e:
            raise RuntimeError(f"Invalid Query DSL for index '{index_name}': {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to execute query on index '{index_name}': {str(e)}") from e

    def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._client:
            self._client.close()
            self._client = None
