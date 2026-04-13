"""
Unit tests for llm_client.py

Tests model verification, DSL generation, timeout handling, and error categorization
with mocked HTTP responses.
Following TDD constitution mandate.
"""

import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import ConnectionError, Timeout, RequestException


def _make_config():
    config = MagicMock()
    config.VLLM_URL = 'http://localhost:1234/v1'
    config.VLLM_MODEL = 'qwen/qwen3-4b-2507'
    config.LLM_TEMPERATURE = 0.1
    config.LLM_MAX_TOKENS = 500
    return config


class TestVLLMClientVerifyModel:
    """Test model availability verification"""

    def test_verify_model_returns_true_when_server_up(self):
        """Test verify_model() returns True when API responds 200"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp

            client = VLLMClient(_make_config())
            assert client.verify_model() is True
            mock_get.assert_called_once_with('http://localhost:1234/v1/models', timeout=5)

    def test_verify_model_returns_false_when_server_down(self):
        """Test verify_model() returns False on ConnectionError"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.get', side_effect=ConnectionError()):
            client = VLLMClient(_make_config())
            assert client.verify_model() is False

    def test_verify_model_returns_false_on_non_200(self):
        """Test verify_model() returns False on non-200 status"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_get.return_value = mock_resp

            client = VLLMClient(_make_config())
            assert client.verify_model() is False


class TestVLLMClientGenerateDSL:
    """Test DSL generation"""

    def _mock_response(self, content: str, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = {
            'choices': [{'message': {'content': content}}]
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_generate_dsl_returns_llm_text(self):
        """Test generate_dsl() returns the content from LLM response"""
        from src.llm_client import VLLMClient

        expected = '{"query": {"match_all": {}}}'
        with patch('src.llm_client.requests.post') as mock_post:
            mock_post.return_value = self._mock_response(expected)

            client = VLLMClient(_make_config())
            result = client.generate_dsl('some prompt')

            assert result == expected

    def test_generate_dsl_uses_correct_endpoint(self):
        """Test generate_dsl() posts to /v1/chat/completions"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.post') as mock_post:
            mock_post.return_value = self._mock_response('{}')

            client = VLLMClient(_make_config())
            client.generate_dsl('prompt')

            call_url = mock_post.call_args[0][0]
            assert call_url == 'http://localhost:1234/v1/chat/completions'

    def test_generate_dsl_passes_temperature_and_max_tokens(self):
        """Test generate_dsl() sends temperature and max_tokens in payload"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.post') as mock_post:
            mock_post.return_value = self._mock_response('{}')

            client = VLLMClient(_make_config())
            client.generate_dsl('prompt', temperature=0.5, max_tokens=200)

            payload = mock_post.call_args[1]['json']
            assert payload['temperature'] == 0.5
            assert payload['max_tokens'] == 200

    def test_generate_dsl_uses_config_defaults(self):
        """Test generate_dsl() falls back to config temperature/max_tokens"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.post') as mock_post:
            mock_post.return_value = self._mock_response('{}')

            client = VLLMClient(_make_config())
            client.generate_dsl('prompt')

            payload = mock_post.call_args[1]['json']
            assert payload['temperature'] == 0.1
            assert payload['max_tokens'] == 500

    def test_generate_dsl_raises_timeout_on_slow_server(self):
        """Test generate_dsl() raises Timeout when request times out"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.post', side_effect=Timeout()):
            client = VLLMClient(_make_config())
            with pytest.raises(Timeout):
                client.generate_dsl('prompt')

    def test_generate_dsl_raises_connection_error_when_server_down(self):
        """Test generate_dsl() raises ConnectionError when server unreachable"""
        from src.llm_client import VLLMClient

        with patch('src.llm_client.requests.post', side_effect=ConnectionError()):
            client = VLLMClient(_make_config())
            with pytest.raises(ConnectionError):
                client.generate_dsl('prompt')

    def test_generate_dsl_strips_whitespace_from_response(self):
        """Test generate_dsl() strips leading/trailing whitespace from LLM output"""
        from src.llm_client import VLLMClient

        raw = '  \n{"query": {"match_all": {}}}\n  '
        with patch('src.llm_client.requests.post') as mock_post:
            mock_post.return_value = self._mock_response(raw)

            client = VLLMClient(_make_config())
            result = client.generate_dsl('prompt')

            assert result == raw.strip()
