"""
Unit tests for es_client.py

Tests connection pooling, health check, mapping retrieval, query execution
with mocked Elasticsearch responses.
Following TDD constitution mandate.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestESClientConnect:
    """Test ESClient connection management"""

    def test_connect_creates_elasticsearch_client(self):
        """Test that connect() creates and returns an Elasticsearch client"""
        from src.es_client import ESClient

        mock_config = MagicMock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            result = es.connect()

            mock_es_cls.assert_called_once()
            assert result == mock_client

    def test_connect_reuses_existing_connection(self):
        """Test that connect() returns cached client on second call"""
        from src.es_client import ESClient

        mock_config = MagicMock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            first = es.connect()
            second = es.connect()

            # Elasticsearch constructor called only once
            assert mock_es_cls.call_count == 1
            assert first is second

    def test_connect_raises_on_ping_failure(self):
        """Test that connect() raises ConnectionError when ping fails"""
        from src.es_client import ESClient
        from elasticsearch.exceptions import ConnectionError

        mock_config = MagicMock()
        mock_config.ES_HOST = 'localhost'
        mock_config.ES_PORT = 9200
        mock_config.ES_USER = 'elastic'
        mock_config.ES_PASSWORD = 'elastic'

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = False
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            with pytest.raises(ConnectionError):
                es.connect()


class TestESClientHealthCheck:
    """Test ESClient health check"""

    def test_check_health_returns_cluster_info(self):
        """Test check_health() returns cluster health dict"""
        from src.es_client import ESClient

        mock_config = MagicMock()

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_health = MagicMock()
            mock_health.body = {'status': 'green', 'cluster_name': 'test'}
            mock_client.cluster.health.return_value = mock_health
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            result = es.check_health()

            assert result['status'] == 'green'
            assert result['cluster_name'] == 'test'


class TestESClientGetMapping:
    """Test ESClient mapping retrieval"""

    def test_get_mapping_returns_index_mapping(self):
        """Test get_mapping() returns mapping dict for given index"""
        from src.es_client import ESClient

        mock_config = MagicMock()
        expected_mapping = {
            'moi-vehicle-info-v1': {
                'mappings': {
                    'properties': {
                        'VRG_PLTNUM': {'type': 'text'}
                    }
                }
            }
        }

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_mapping_resp = MagicMock()
            mock_mapping_resp.body = expected_mapping
            mock_client.indices.get_mapping.return_value = mock_mapping_resp
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            result = es.get_mapping('moi-vehicle-info-v1')

            assert result == expected_mapping
            mock_client.indices.get_mapping.assert_called_once_with(index='moi-vehicle-info-v1')

    def test_get_mapping_raises_on_missing_index(self):
        """Test get_mapping() raises RuntimeError when index not found"""
        from src.es_client import ESClient
        from elasticsearch.exceptions import NotFoundError

        mock_config = MagicMock()

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.indices.get_mapping.side_effect = NotFoundError(
                message='index not found', meta=MagicMock(), body={}
            )
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            with pytest.raises(RuntimeError, match="not found"):
                es.get_mapping('nonexistent-index')


class TestESClientExecuteQuery:
    """Test ESClient query execution"""

    def test_execute_query_returns_hits(self):
        """Test execute_query() returns ES hits structure"""
        from src.es_client import ESClient

        mock_config = MagicMock()
        expected_response = {
            'hits': {
                'total': {'value': 2},
                'hits': [
                    {'_source': {'VRG_PLTNUM': 'A12345'}},
                    {'_source': {'VRG_PLTNUM': 'B67890'}},
                ]
            }
        }
        query_dsl = {'query': {'term': {'VRG_PLTNUM.keyword': 'A12345'}}}

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_resp = MagicMock()
            mock_resp.body = expected_response
            mock_client.search.return_value = mock_resp
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            result = es.execute_query('moi-vehicle-info-v1', query_dsl)

            assert result['hits']['total']['value'] == 2
            mock_client.search.assert_called_once_with(
                index='moi-vehicle-info-v1', body=query_dsl
            )

    def test_execute_query_raises_on_bad_dsl(self):
        """Test execute_query() raises RuntimeError on invalid DSL"""
        from src.es_client import ESClient
        from elasticsearch.exceptions import RequestError

        mock_config = MagicMock()

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_meta = MagicMock()
            mock_meta.status = 400
            mock_client.search.side_effect = RequestError(
                message='x_content_parse_exception', meta=mock_meta, body={'error': 'malformed query'}
            )
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            with pytest.raises(RuntimeError, match="Invalid Query DSL"):
                es.execute_query('moi-vehicle-info-v1', {'query': {'bad': {}}})

    def test_close_clears_client(self):
        """Test close() clears the cached client"""
        from src.es_client import ESClient

        mock_config = MagicMock()

        with patch('src.es_client.Elasticsearch') as mock_es_cls:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_es_cls.return_value = mock_client

            es = ESClient(mock_config)
            es.connect()
            assert es._client is not None

            es.close()
            assert es._client is None
