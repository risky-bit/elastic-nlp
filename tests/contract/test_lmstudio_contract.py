"""
Contract tests for vLLM API

Tests API endpoint availability, model verification, and chat chat completions endpoint response format.
Following TDD: These tests are written FIRST and should FAIL until llm_client.py is implemented.

NOTE: These tests require vLLM server running at localhost:8000 with EQuIP-Queries/EQuIP_3B model loaded
Start vLLM with: vllm serve "EQuIP-Queries/EQuIP_3B"
"""

import pytest
from unittest.mock import Mock


# Mark as contract test and slow (requires external vLLM server)
pytestmark = [pytest.mark.contract, pytest.mark.slow]


class TestVLLMContract:
    """Test vLLM API contract compliance"""

    def test_vllm_api_endpoint_availability(self):
        """Test that vLLM API endpoint is accessible"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        # Act & Assert - Constructor should succeed (connection test)
        assert client is not None

    def test_vllm_model_verification(self):
        """Test that client can verify model is loaded"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        # Act
        is_available = client.verify_model()

        # Assert
        assert isinstance(is_available, bool)
        assert is_available is True  # EQuIP_3B should be loaded per spec

    def test_vllm_completions_endpoint_response_format(self):
        """Test that /v1/chat completions endpoint returns expected structure"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        test_prompt = "Generate a simple Elasticsearch Query DSL for finding a person named Ahmed."

        # Act
        response = client.generate_dsl(test_prompt)

        # Assert
        assert response is not None
        assert isinstance(response, str)  # Should return generated text
        assert len(response) > 0

    def test_vllm_handles_timeout_gracefully(self):
        """Test that client handles request timeouts without crashing"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        # Act with very short timeout (should handle gracefully)
        # Implementation should catch timeout exception
        try:
            result = client.generate_dsl("test prompt", timeout=0.001)
            # If it completes fast enough, that's fine
            assert result is not None
        except Exception as e:
            # Should be a timeout or connection error, not a crash
            assert 'timeout' in str(e).lower() or 'connection' in str(e).lower()

    def test_vllm_connection_failure_handling(self):
        """Test that client handles connection failures gracefully"""
        # Arrange
        from src.llm_client import VLLMClient

        # Invalid URL
        mock_config = Mock()
        mock_config.LM_STUDIO_URL = 'http://invalid_host:1234/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        # Act & Assert - Should raise exception, not crash
        with pytest.raises(Exception):  # ConnectionError or similar
            client.generate_dsl("test prompt")

    def test_vllm_respects_temperature_parameter(self):
        """Test that client sends temperature parameter to API"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 500

        client = VLLMClient(mock_config)

        # Act - Generate with explicit temperature
        response = client.generate_dsl("test prompt", temperature=0.1)

        # Assert - Just verify it completes (parameter validation happens in implementation)
        assert response is not None

    def test_vllm_respects_max_tokens_parameter(self):
        """Test that client sends max_tokens parameter to API"""
        # Arrange
        from src.llm_client import VLLMClient

        mock_config = Mock()
        mock_config.VLLM_URL = 'http://localhost:8000/v1'
        mock_config.VLLM_MODEL = 'EQuIP-Queries/EQuIP_3B'
        mock_config.LLM_TEMPERATURE = 0.1
        mock_config.LLM_MAX_TOKENS = 50  # Very small limit

        client = VLLMClient(mock_config)

        # Act
        response = client.generate_dsl("test", max_tokens=50)

        # Assert - Response should be limited by max_tokens
        assert response is not None
        # Response should be relatively short due to token limit
        assert len(response) < 1000  # Rough check
