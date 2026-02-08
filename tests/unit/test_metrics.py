"""
Unit tests for metrics.py

Tests MetricsCalculator methods for DSL validity rate, result accuracy rate, and report generation.
Following TDD: These tests are written FIRST and should FAIL until metrics.py is implemented.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock


class TestMetricsCalculator:
    """Test MetricsCalculator class for baseline metrics calculation"""

    def test_calculate_dsl_validity_rate(self):
        """Test DSL validity rate calculation"""
        # Arrange
        from src.metrics import MetricsCalculator

        # Mock log data: 7 out of 10 queries have valid DSL
        mock_logs = [
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': True, 'execution_status': 'success'},
            {'is_valid_json': False, 'execution_status': 'validation_failed'},
            {'is_valid_json': False, 'execution_status': 'validation_failed'},
            {'is_valid_json': False, 'execution_status': 'validation_failed'},
        ]

        calculator = MetricsCalculator()

        # Act
        validity_rate = calculator.calculate_dsl_validity_rate(mock_logs)

        # Assert
        assert validity_rate == 0.7  # 7/10 = 70%

    def test_calculate_result_accuracy_rate(self):
        """Test result accuracy rate calculation"""
        # Arrange
        from src.metrics import MetricsCalculator

        # Mock log data: 8 out of 10 queries succeeded
        mock_logs = [
            {'execution_status': 'success', 'result_count': 5},
            {'execution_status': 'success', 'result_count': 3},
            {'execution_status': 'success', 'result_count': 0},  # Valid but no results
            {'execution_status': 'success', 'result_count': 12},
            {'execution_status': 'success', 'result_count': 1},
            {'execution_status': 'success', 'result_count': 7},
            {'execution_status': 'success', 'result_count': 2},
            {'execution_status': 'success', 'result_count': 15},
            {'execution_status': 'execution_failed', 'result_count': None},
            {'execution_status': 'validation_failed', 'result_count': None},
        ]

        calculator = MetricsCalculator()

        # Act
        accuracy_rate = calculator.calculate_result_accuracy_rate(mock_logs)

        # Assert
        assert accuracy_rate == 0.8  # 8/10 = 80%

    def test_calculate_latency_stats(self):
        """Test latency statistics calculation"""
        # Arrange
        from src.metrics import MetricsCalculator

        mock_logs = [
            {'llm_latency_ms': 1200, 'es_latency_ms': 45, 'total_latency_ms': 1245},
            {'llm_latency_ms': 1500, 'es_latency_ms': 52, 'total_latency_ms': 1552},
            {'llm_latency_ms': 1100, 'es_latency_ms': 38, 'total_latency_ms': 1138},
            {'llm_latency_ms': 1800, 'es_latency_ms': 67, 'total_latency_ms': 1867},
        ]

        calculator = MetricsCalculator()

        # Act
        stats = calculator.calculate_latency_stats(mock_logs)

        # Assert
        assert 'avg_llm_latency_ms' in stats
        assert 'avg_es_latency_ms' in stats
        assert 'avg_total_latency_ms' in stats
        assert stats['avg_llm_latency_ms'] == 1400.0  # (1200+1500+1100+1800)/4
        assert stats['avg_es_latency_ms'] == 50.5    # (45+52+38+67)/4
        assert stats['avg_total_latency_ms'] == 1450.5

    def test_generate_report(self):
        """Test metrics report generation"""
        # Arrange
        from src.metrics import MetricsCalculator

        mock_logs = [
            {
                'nl_query': 'Find Ahmed',
                'index_name': 'person_details',
                'is_valid_json': True,
                'execution_status': 'success',
                'result_count': 5,
                'llm_latency_ms': 1200,
                'es_latency_ms': 45,
                'total_latency_ms': 1245,
            },
            {
                'nl_query': 'Find Toyota',
                'index_name': 'vehicle',
                'is_valid_json': True,
                'execution_status': 'success',
                'result_count': 3,
                'llm_latency_ms': 1500,
                'es_latency_ms': 52,
                'total_latency_ms': 1552,
            },
            {
                'nl_query': 'Bad query',
                'index_name': 'person_details',
                'is_valid_json': False,
                'execution_status': 'validation_failed',
                'result_count': None,
                'llm_latency_ms': 1100,
                'es_latency_ms': None,
                'total_latency_ms': 1100,
            },
        ]

        calculator = MetricsCalculator()

        # Act
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'metrics.json')
            calculator.generate_report(mock_logs, output_path)

            # Assert
            assert os.path.exists(output_path)

            with open(output_path, 'r') as f:
                report = json.load(f)

            assert 'corpus_size' in report
            assert 'dsl_validity_rate' in report
            assert 'result_accuracy_rate' in report
            assert 'avg_llm_latency_ms' in report
            assert 'avg_es_latency_ms' in report

            assert report['corpus_size'] == 3
            assert report['dsl_validity_rate'] == pytest.approx(0.666, abs=0.01)  # 2/3
            assert report['result_accuracy_rate'] == pytest.approx(0.666, abs=0.01)  # 2/3

    def test_parse_logs_from_file(self):
        """Test parsing query translation logs from JSON Lines file"""
        # Arrange
        from src.metrics import MetricsCalculator

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test_logs.jsonl')

            # Create sample log file
            with open(log_file, 'w') as f:
                f.write(json.dumps({'nl_query': 'Query 1', 'is_valid_json': True}) + '\n')
                f.write(json.dumps({'nl_query': 'Query 2', 'is_valid_json': False}) + '\n')
                f.write(json.dumps({'nl_query': 'Query 3', 'is_valid_json': True}) + '\n')

            calculator = MetricsCalculator()

            # Act
            logs = calculator.parse_logs(log_file)

            # Assert
            assert len(logs) == 3
            assert logs[0]['nl_query'] == 'Query 1'
            assert logs[1]['nl_query'] == 'Query 2'
            assert logs[2]['nl_query'] == 'Query 3'
