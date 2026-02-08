"""
Integration tests for metrics.py

Tests end-to-end metrics report generation from log files.
Following TDD: These tests are written FIRST and should FAIL until metrics.py is implemented.
"""

import pytest
import json
import tempfile
import os


class TestMetricsIntegration:
    """Test end-to-end metrics report generation"""

    def test_metrics_report_generation_from_log_file(self):
        """Test reading logs from file and generating metrics report"""
        # Arrange
        from src.metrics import MetricsCalculator

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'query_translations.jsonl')
            report_file = os.path.join(tmpdir, 'metrics_report.json')

            # Create sample log file with realistic query translation data
            sample_logs = [
                {
                    'timestamp': '2026-02-05T10:00:00.000Z',
                    'level': 'INFO',
                    'message': 'Query translation',
                    'nl_query': 'Find person named Ahmed',
                    'index_name': 'person_details',
                    'index_mapping_hash': 'abc123',
                    'prompt': 'Generate DSL...',
                    'generated_dsl': '{"query": {"match": {"name": "Ahmed"}}}',
                    'is_valid_json': True,
                    'execution_status': 'success',
                    'result_count': 5,
                    'llm_latency_ms': 1200.5,
                    'es_latency_ms': 45.2,
                    'total_latency_ms': 1245.7,
                    'llm_model': 'EQuIP-Queries/EQuIP_3B',
                    'llm_temperature': 0.1,
                },
                {
                    'timestamp': '2026-02-05T10:01:00.000Z',
                    'level': 'INFO',
                    'message': 'Query translation',
                    'nl_query': 'Find Toyota vehicles',
                    'index_name': 'vehicle',
                    'index_mapping_hash': 'def456',
                    'prompt': 'Generate DSL...',
                    'generated_dsl': '{"query": {"match": {"make": "Toyota"}}}',
                    'is_valid_json': True,
                    'execution_status': 'success',
                    'result_count': 12,
                    'llm_latency_ms': 1350.0,
                    'es_latency_ms': 52.8,
                    'total_latency_ms': 1402.8,
                    'llm_model': 'EQuIP-Queries/EQuIP_3B',
                    'llm_temperature': 0.1,
                },
                {
                    'timestamp': '2026-02-05T10:02:00.000Z',
                    'level': 'INFO',
                    'message': 'Query translation',
                    'nl_query': 'Invalid query xyz',
                    'index_name': 'person_details',
                    'index_mapping_hash': 'abc123',
                    'prompt': 'Generate DSL...',
                    'generated_dsl': '{"invalid json',
                    'is_valid_json': False,
                    'execution_status': 'validation_failed',
                    'result_count': None,
                    'llm_latency_ms': 1100.0,
                    'es_latency_ms': None,
                    'total_latency_ms': 1100.0,
                    'llm_model': 'EQuIP-Queries/EQuIP_3B',
                    'llm_temperature': 0.1,
                },
            ]

            # Write logs to file (JSON Lines format)
            with open(log_file, 'w') as f:
                for log in sample_logs:
                    f.write(json.dumps(log) + '\n')

            calculator = MetricsCalculator()

            # Act
            logs = calculator.parse_logs(log_file)
            calculator.generate_report(logs, report_file)

            # Assert
            assert os.path.exists(report_file)

            with open(report_file, 'r') as f:
                report = json.load(f)

            # Verify report structure
            assert 'report_id' in report
            assert 'generated_at' in report
            assert 'corpus_size' in report
            assert 'dsl_validity_rate' in report
            assert 'result_accuracy_rate' in report
            assert 'avg_llm_latency_ms' in report
            assert 'avg_es_latency_ms' in report
            assert 'avg_total_latency_ms' in report

            # Verify calculated values
            assert report['corpus_size'] == 3
            assert report['dsl_validity_rate'] == pytest.approx(0.666, abs=0.01)  # 2/3
            assert report['result_accuracy_rate'] == pytest.approx(0.666, abs=0.01)  # 2/3
            assert report['avg_llm_latency_ms'] == pytest.approx(1216.8, abs=0.1)
            assert report['avg_es_latency_ms'] == pytest.approx(49.0, abs=0.1)  # Average of non-None values

    def test_metrics_report_includes_timestamp_and_id(self):
        """Test that metrics report includes unique ID and timestamp"""
        # Arrange
        from src.metrics import MetricsCalculator

        mock_logs = [
            {'is_valid_json': True, 'execution_status': 'success', 'result_count': 1,
             'llm_latency_ms': 1000, 'es_latency_ms': 50, 'total_latency_ms': 1050}
        ]

        calculator = MetricsCalculator()

        # Act
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'report.json')
            calculator.generate_report(mock_logs, output_path)

            with open(output_path, 'r') as f:
                report = json.load(f)

        # Assert
        assert 'report_id' in report
        assert 'generated_at' in report
        assert len(report['report_id']) > 0
        # Timestamp should be ISO 8601 format
        assert 'T' in report['generated_at']
        assert 'Z' in report['generated_at']

    def test_empty_log_file_handling(self):
        """Test that calculator handles empty log files gracefully"""
        # Arrange
        from src.metrics import MetricsCalculator

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'empty.jsonl')

            # Create empty file
            with open(log_file, 'w') as f:
                pass

            calculator = MetricsCalculator()

            # Act
            logs = calculator.parse_logs(log_file)

            # Assert
            assert logs == []
            assert len(logs) == 0
