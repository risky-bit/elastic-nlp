"""
Contract tests for Elasticsearch API

Tests cluster health check, index existence verification, and mapping retrieval.
Following TDD: These tests are written FIRST and should FAIL until es_client.py is implemented.

NOTE: These tests require Elasticsearch running at localhost:9200
"""

import pytest
from unittest.mock import Mock, patch


# Mark as contract test and slow (requires external ES)
pytestmark = [pytest.mark.contract, pytest.mark.slow]


class TestElasticsearchContract:
    """Test Elasticsearch API contract compliance"""

    def test_elasticsearch_cluster_health_check(self):
        """Test that cluster health endpoint returns expected structure"""
        # Arrange
        from src.es_client import ESClient
        from src.config import Config

        # Mock config for test
        mock_config = Mock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        client = ESClient(mock_config)

        # Act
        health = client.check_health()

        # Assert
        assert health is not None
        assert 'status' in health  # Should have status field (green, yellow, red)
        assert health['status'] in ['green', 'yellow', 'red']

    def test_elasticsearch_index_existence_verification(self):
        """Test that client can verify index existence"""
        # Arrange
        from src.es_client import ESClient

        mock_config = Mock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        client = ESClient(mock_config)

        # Act - Check for known index (person_details should exist per spec)
        exists = client.index_exists('person_details')

        # Assert
        assert isinstance(exists, bool)
        # If this fails, ensure person_details index exists in your ES instance

    def test_elasticsearch_mapping_retrieval(self):
        """Test that client can retrieve index mapping"""
        # Arrange
        from src.es_client import ESClient

        mock_config = Mock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        client = ESClient(mock_config)

        # Act
        mapping = client.get_mapping('person_details')

        # Assert
        assert mapping is not None
        assert isinstance(mapping, dict)
        # Mapping should have structure: {index_name: {mappings: {...}}}
        assert 'person_details' in mapping or 'mappings' in mapping

    def test_elasticsearch_connection_failure_handling(self):
        """Test that client handles connection failures gracefully"""
        # Arrange
        from src.es_client import ESClient

        # Invalid config (non-existent host)
        mock_config = Mock()
        mock_config.ES_HOST = 'invalid_host_that_does_not_exist'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        client = ESClient(mock_config)

        # Act & Assert - Should raise or return error, not crash
        with pytest.raises(Exception):  # ConnectionError or similar
            client.check_health()

    def test_elasticsearch_query_execution(self):
        """Test that client can execute Query DSL against an index"""
        # Arrange
        from src.es_client import ESClient

        mock_config = Mock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        client = ESClient(mock_config)

        # Simple match_all query
        query_dsl = {
            "query": {
                "match_all": {}
            },
            "size": 1
        }

        # Act
        results = client.execute_query('person_details', query_dsl)

        # Assert
        assert results is not None
        assert isinstance(results, dict)
        assert 'hits' in results  # ES response structure
        assert 'total' in results['hits']
