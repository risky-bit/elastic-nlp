"""
Unit tests for cli.py

Tests CLI commands: query, batch, metrics
Following TDD: These tests are written FIRST and should FAIL until cli.py is implemented.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch
from click.testing import CliRunner


class TestCLIQuery:
    """Test CLI query command for NL-to-DSL translation"""

    def test_query_command_basic_usage(self):
        """Test basic query command execution"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        # Mock the query generator to return success
        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'success',
                'results': {
                    'hits': {
                        'total': {'value': 5},
                        'hits': [
                            {'_source': {'name': 'Ahmed Al-Mansoori'}}
                        ]
                    }
                }
            }
            MockQueryGenerator.return_value = mock_generator

            # Act
            result = runner.invoke(cli, ['query', 'Find person named Ahmed', '--index', 'person_details'])

            # Assert
            assert result.exit_code == 0
            assert 'success' in result.output.lower()

    def test_query_command_with_output_file(self):
        """Test query command with output file option"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'success',
                'results': {'hits': {'total': {'value': 1}, 'hits': []}}
            }
            MockQueryGenerator.return_value = mock_generator

            with tempfile.TemporaryDirectory() as tmpdir:
                output_file = os.path.join(tmpdir, 'results.json')

                # Act
                result = runner.invoke(cli, [
                    'query',
                    'Find Ahmed',
                    '--index', 'person_details',
                    '--output', output_file
                ])

                # Assert
                assert result.exit_code == 0
                assert os.path.exists(output_file)

                with open(output_file, 'r') as f:
                    output_data = json.load(f)
                    assert 'status' in output_data
                    assert output_data['status'] == 'success'

    def test_query_command_validation_failed(self):
        """Test query command when DSL validation fails"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'validation_failed',
                'error': 'Invalid JSON generated'
            }
            MockQueryGenerator.return_value = mock_generator

            # Act
            result = runner.invoke(cli, ['query', 'Bad query xyz', '--index', 'person_details'])

            # Assert
            # CLI should show error but not crash
            assert 'validation_failed' in result.output.lower() or 'error' in result.output.lower()

    def test_query_command_missing_index(self):
        """Test query command fails when index is not specified"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ['query', 'Find Ahmed'])

        # Assert
        # Should fail due to missing required --index option
        assert result.exit_code != 0

    def test_query_command_with_verbose_flag(self):
        """Test query command with verbose output"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'success',
                'generated_dsl': '{"query": {"match": {"name": "Ahmed"}}}',
                'results': {'hits': {'total': {'value': 1}, 'hits': []}}
            }
            MockQueryGenerator.return_value = mock_generator

            # Act
            result = runner.invoke(cli, [
                'query',
                'Find Ahmed',
                '--index', 'person_details',
                '--verbose'
            ])

            # Assert
            assert result.exit_code == 0
            # Verbose mode should show generated DSL
            if 'generated_dsl' in mock_generator.generate_query.return_value:
                # Output should contain query details
                assert 'query' in result.output.lower() or 'match' in result.output.lower()


class TestCLIBatch:
    """Test CLI batch command for processing multiple queries"""

    def test_batch_command_basic_usage(self):
        """Test batch command with queries file"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'success',
                'results': {'hits': {'total': {'value': 1}, 'hits': []}}
            }
            MockQueryGenerator.return_value = mock_generator

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create test queries file
                queries_file = os.path.join(tmpdir, 'queries.txt')
                with open(queries_file, 'w') as f:
                    f.write('Find person named Ahmed\n')
                    f.write('Find all Pakistanis\n')
                    f.write('Find vehicles made by Toyota\n')

                # Act
                result = runner.invoke(cli, [
                    'batch',
                    queries_file,
                    '--index', 'person_details'
                ])

                # Assert
                assert result.exit_code == 0
                # Should have processed 3 queries
                assert mock_generator.generate_query.call_count == 3

    def test_batch_command_with_output_file(self):
        """Test batch command saves results to file"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with patch('src.cli.QueryGenerator') as MockQueryGenerator:
            mock_generator = Mock()
            mock_generator.generate_query.return_value = {
                'status': 'success',
                'results': {'hits': {'total': {'value': 0}, 'hits': []}}
            }
            MockQueryGenerator.return_value = mock_generator

            with tempfile.TemporaryDirectory() as tmpdir:
                queries_file = os.path.join(tmpdir, 'queries.txt')
                with open(queries_file, 'w') as f:
                    f.write('Find Ahmed\n')

                output_file = os.path.join(tmpdir, 'batch_results.jsonl')

                # Act
                result = runner.invoke(cli, [
                    'batch',
                    queries_file,
                    '--index', 'person_details',
                    '--output', output_file
                ])

                # Assert
                assert result.exit_code == 0
                assert os.path.exists(output_file)


class TestCLIMetrics:
    """Test CLI metrics command for calculating baseline metrics"""

    def test_metrics_command_basic_usage(self):
        """Test metrics command generates report from logs"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample log file
            log_file = os.path.join(tmpdir, 'query_translations.jsonl')
            with open(log_file, 'w') as f:
                f.write(json.dumps({
                    'nl_query': 'Find Ahmed',
                    'is_valid_json': True,
                    'execution_status': 'success',
                    'llm_latency_ms': 1200,
                    'es_latency_ms': 45,
                    'total_latency_ms': 1245
                }) + '\n')

            output_file = os.path.join(tmpdir, 'metrics.json')

            # Act
            result = runner.invoke(cli, [
                'metrics',
                log_file,
                '--output', output_file
            ])

            # Assert
            assert result.exit_code == 0
            assert os.path.exists(output_file)

            with open(output_file, 'r') as f:
                report = json.load(f)
                assert 'dsl_validity_rate' in report
                assert 'result_accuracy_rate' in report

    def test_metrics_command_empty_log_file(self):
        """Test metrics command handles empty log file gracefully"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'empty.jsonl')
            with open(log_file, 'w') as f:
                pass  # Empty file

            output_file = os.path.join(tmpdir, 'metrics.json')

            # Act
            result = runner.invoke(cli, [
                'metrics',
                log_file,
                '--output', output_file
            ])

            # Assert
            # Should handle gracefully (may show warning but not crash)
            assert os.path.exists(output_file)

    def test_metrics_command_missing_log_file(self):
        """Test metrics command fails gracefully when log file doesn't exist"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        # Act
        result = runner.invoke(cli, [
            'metrics',
            '/nonexistent/path/logs.jsonl',
            '--output', '/tmp/metrics.json'
        ])

        # Assert
        # Should fail but not crash
        assert 'error' in result.output.lower() or result.exit_code != 0


class TestCLIHelp:
    """Test CLI help and version commands"""

    def test_cli_help(self):
        """Test CLI shows help message"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ['--help'])

        # Assert
        assert result.exit_code == 0
        assert 'query' in result.output.lower()
        assert 'batch' in result.output.lower()
        assert 'metrics' in result.output.lower()

    def test_query_command_help(self):
        """Test query command shows help"""
        # Arrange
        from src.cli import cli

        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ['query', '--help'])

        # Assert
        assert result.exit_code == 0
        assert 'index' in result.output.lower()
