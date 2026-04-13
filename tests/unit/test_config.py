"""
Unit tests for config.py

Tests environment variable loading, validation, type conversion, and error handling.
Following TDD: These tests are written FIRST and should FAIL until config.py is implemented.
"""

import pytest
import os
import importlib
import sys
from unittest.mock import patch


class TestConfig:
    """Test Config class environment variable handling"""

    def test_config_loads_required_variables(self):
        """Test that Config loads all required environment variables"""
        # Arrange
        env_vars = {
            'ES_HOST': 'localhost',
            'ES_PORT': '9200',
            'ES_USER': 'elastic',
            'ES_PASSWORD': 'test_password',
            'VLLM_URL': 'http://localhost:8000/v1',
            'VLLM_MODEL': 'EQuIP-Queries/EQuIP_3B',
        }

        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            import src.config as config_module
            importlib.reload(config_module)
            Config = config_module.Config

            assert Config.ES_HOST == 'localhost'
            assert Config.ES_PORT == 9200  # Should be integer
            assert Config.ES_USER == 'elastic'
            assert Config.ES_PASSWORD == 'test_password'
            assert Config.VLLM_URL == 'http://localhost:8000/v1'
            assert Config.VLLM_MODEL == 'EQuIP-Queries/EQuIP_3B'

    def test_config_converts_port_to_integer(self):
        """Test that ES_PORT is converted from string to integer"""
        # Arrange
        env_vars = {
            'ES_HOST': 'localhost',
            'ES_PORT': '9200',  # String in env var
            'ES_USER': 'elastic',
            'ES_PASSWORD': 'test_password',
            'VLLM_URL': 'http://localhost:8000/v1',
            'VLLM_MODEL': 'EQuIP-Queries/EQuIP_3B',
        }

        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            from src.config import Config

            assert isinstance(Config.ES_PORT, int)
            assert Config.ES_PORT == 9200

    def test_config_applies_default_values(self):
        """Test that optional variables get default values"""
        # Arrange
        env_vars = {
            'ES_HOST': 'localhost',
            'ES_PORT': '9200',
            'ES_USER': 'elastic',
            'ES_PASSWORD': 'test_password',
            'VLLM_URL': 'http://localhost:8000/v1',
            'VLLM_MODEL': 'EQuIP-Queries/EQuIP_3B',
            # LLM_TEMPERATURE and LLM_MAX_TOKENS not provided
        }

        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            from src.config import Config

            assert Config.LLM_TEMPERATURE == 0.1  # Default
            assert Config.LLM_MAX_TOKENS == 500   # Default

    def test_config_validation_fails_on_missing_required_vars(self):
        """Test that validation raises error when required variables are missing"""
        # Arrange
        env_vars = {
            'ES_HOST': 'localhost',
            'ES_PORT': '9200',
            # Missing ES_USER and ES_PASSWORD
        }

        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            from src.config import Config

            with pytest.raises(ValueError, match="ES_USER.*ES_PASSWORD"):
                Config.validate()

    def test_config_validation_passes_with_all_required_vars(self):
        """Test that validation succeeds when all required variables are present"""
        # Arrange
        env_vars = {
            'ES_HOST': 'localhost',
            'ES_PORT': '9200',
            'ES_USER': 'elastic',
            'ES_PASSWORD': 'test_password',
            'VLLM_URL': 'http://localhost:8000/v1',
            'VLLM_MODEL': 'EQuIP-Queries/EQuIP_3B',
        }

        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            from src.config import Config

            # Should not raise
            Config.validate()
