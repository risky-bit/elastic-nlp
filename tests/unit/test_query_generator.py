"""
Unit tests for query_generator.py

Tests QueryGenerator orchestration: prompt construction, DSL validation, query generation.
Following TDD: These tests are written FIRST and should FAIL until query_generator.py is implemented.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class TestQueryGenerator:
    """Test QueryGenerator class for query translation orchestration"""

    def test_construct_prompt(self):
        """Test prompt construction with index mapping and NL query"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        nl_query = "Find person named Ahmed"
        index_mapping = {
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "age": {"type": "integer"}
                }
            }
        }

        # Act
        prompt = generator.construct_prompt(nl_query, index_mapping)

        # Assert
        assert isinstance(prompt, str)
        assert "Find person named Ahmed" in prompt
        assert "name" in prompt  # Mapping should be in prompt
        assert "age" in prompt

    def test_validate_dsl_valid_json(self):
        """Test DSL validation with valid Query DSL"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        valid_dsl = '{"query": {"match": {"name": "Ahmed"}}}'

        # Act
        is_valid, parsed_dsl, error = generator.validate_dsl(valid_dsl)

        # Assert
        assert is_valid is True
        assert parsed_dsl == {"query": {"match": {"name": "Ahmed"}}}
        assert error is None

    def test_validate_dsl_invalid_json(self):
        """Test DSL validation with invalid JSON"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        invalid_dsl = '{"query": invalid json'

        # Act
        is_valid, parsed_dsl, error = generator.validate_dsl(invalid_dsl)

        # Assert
        assert is_valid is False
        assert parsed_dsl is None
        assert error is not None
        assert "JSON" in error or "json" in error

    def test_validate_dsl_missing_query_key(self):
        """Test DSL validation rejects JSON without 'query' key"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        dsl_without_query = '{"match": {"name": "Ahmed"}}'

        # Act
        is_valid, parsed_dsl, error = generator.validate_dsl(dsl_without_query)

        # Assert
        assert is_valid is False
        assert error is not None

    def test_generate_query_success(self):
        """Test successful query generation end-to-end"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [{"_source": {"name": "Ahmed"}}]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = '{"query": {"match": {"name": "Ahmed"}}}'

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find Ahmed", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results'] is not None
        assert mock_es_client.get_mapping.called
        assert mock_llm_client.generate_dsl.called
        assert mock_es_client.execute_query.called

    def test_generate_query_handles_invalid_dsl(self):
        """Test that generator handles invalid DSL gracefully"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {"mappings": {"properties": {}}}

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = 'invalid json'

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find Ahmed", "person_details")

        # Assert
        assert result['status'] == 'validation_failed'
        assert 'error' in result
        # Should not call execute_query if validation fails
        assert not mock_es_client.execute_query.called

    def test_load_prompt_template(self):
        """Test loading prompt template from file"""
        # Arrange
        from src.query_generator import QueryGenerator
        import tempfile
        import os

        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Create temporary prompt template
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = os.path.join(tmpdir, 'prompt_v1.txt')
            with open(template_path, 'w') as f:
                f.write("Test prompt template: {mapping} {query}")

            # Act
            template = generator.load_prompt_template(template_path)

            # Assert
            assert template == "Test prompt template: {mapping} {query}"
            assert "{mapping}" in template
            assert "{query}" in template
