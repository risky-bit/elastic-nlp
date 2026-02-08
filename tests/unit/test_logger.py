"""
Unit tests for logger.py

Tests JSON formatter, log file creation, and structured log output format.
Following TDD: These tests are written FIRST and should FAIL until logger.py is implemented.
"""

import pytest
import json
import os
import tempfile
import logging


class TestJSONFormatter:
    """Test JSONFormatter class"""

    def test_json_formatter_creates_valid_json(self):
        """Test that JSONFormatter outputs valid JSON"""
        # Arrange
        from src.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Act
        formatted = formatter.format(record)

        # Assert
        parsed = json.loads(formatted)  # Should not raise
        assert 'timestamp' in parsed
        assert 'level' in parsed
        assert 'message' in parsed

    def test_json_formatter_includes_extra_fields(self):
        """Test that JSONFormatter includes extra fields from record"""
        # Arrange
        from src.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.extra = {'nl_query': 'Find Ahmed', 'index_name': 'person_details'}

        # Act
        formatted = formatter.format(record)

        # Assert
        parsed = json.loads(formatted)
        assert parsed['nl_query'] == 'Find Ahmed'
        assert parsed['index_name'] == 'person_details'

    def test_json_formatter_handles_missing_extra_fields(self):
        """Test that JSONFormatter handles records without extra fields"""
        # Arrange
        from src.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        # No extra field set

        # Act
        formatted = formatter.format(record)

        # Assert
        parsed = json.loads(formatted)  # Should not raise
        assert 'timestamp' in parsed
        assert 'level' in parsed


class TestLoggerSetup:
    """Test logger configuration and setup"""

    def test_setup_query_translation_logger_creates_file_handler(self):
        """Test that setup_query_translation_logger creates file handler for logs/query_translations.jsonl"""
        # Arrange
        from src.logger import setup_query_translation_logger
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'query_translations.jsonl')

            # Act
            logger = setup_query_translation_logger(log_file)

            # Assert
            assert logger is not None
            assert logger.name == 'query_translation'
            assert len(logger.handlers) > 0

            # Log a message
            logger.info('Test log', extra={'test_field': 'test_value'})

            # Verify file was created and contains JSON
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                line = f.readline()
                parsed = json.loads(line)
                assert parsed['message'] == 'Test log'
                assert parsed['test_field'] == 'test_value'

    def test_logger_outputs_structured_json_lines_format(self):
        """Test that logger outputs JSON Lines format (.jsonl)"""
        # Arrange
        from src.logger import setup_query_translation_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')
            logger = setup_query_translation_logger(log_file)

            # Act
            logger.info('Message 1', extra={'field': 'value1'})
            logger.info('Message 2', extra={'field': 'value2'})

            # Assert - Each line should be valid JSON
            with open(log_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2

                parsed1 = json.loads(lines[0])
                assert parsed1['message'] == 'Message 1'
                assert parsed1['field'] == 'value1'

                parsed2 = json.loads(lines[1])
                assert parsed2['message'] == 'Message 2'
                assert parsed2['field'] == 'value2'
