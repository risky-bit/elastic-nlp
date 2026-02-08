"""
Command Line Interface for MOI Elasticsearch NLP Query System

Provides commands:
- query: Translate single NL query to DSL and execute
- batch: Process multiple queries from file
- metrics: Generate baseline metrics report

Following constitution: Reproducibility (IV) - all commands log to query_translations.jsonl
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from src.config import Config
from src.es_client import ESClient
from src.llm_client import VLLMClient
from src.query_generator import QueryGenerator
from src.logger import setup_query_translation_logger
from src.metrics import MetricsCalculator


@click.group()
@click.version_option(version='1.0.0', prog_name='moi-elastic-nlp')
def cli():
    """
    MOI Elasticsearch NLP Query System - Phase 1 Baseline

    Translate natural language queries to Elasticsearch Query DSL.
    """
    pass


@cli.command()
@click.argument('query_text', required=False)
@click.option('--index', help='Target Elasticsearch index name')
@click.option('--output', '-o', type=click.Path(), help='Save results to JSON file')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output including generated DSL')
@click.option('--interactive', '-i', is_flag=True, help='Enter interactive mode for multiple queries')
def query(query_text: Optional[str], index: Optional[str], output: Optional[str], verbose: bool, interactive: bool):
    """
    Translate a natural language query to Elasticsearch DSL and execute it.

    Examples:
        # Single query mode
        moi-elastic-nlp query "Find person named Ahmed" --index person_details

        # Interactive mode
        moi-elastic-nlp query --interactive --index person_details
    """
    try:
        # Initialize components
        config = Config()
        logger = setup_query_translation_logger()

        es_client = ESClient(config)
        es_client.connect()

        llm_client = VLLMClient(config)

        generator = QueryGenerator(es_client, llm_client, config, logger)

        # Interactive mode
        if interactive:
            _run_interactive_mode(generator, index, verbose)
            return

        # Single query mode - require both query_text and index
        if not query_text:
            click.echo(click.style("✗ Error: query_text is required in non-interactive mode", fg='red'))
            click.echo("Use --interactive flag for interactive mode, or provide a query.")
            sys.exit(1)

        if not index:
            click.echo(click.style("✗ Error: --index is required", fg='red'))
            sys.exit(1)

        # Execute single query
        result = _execute_single_query(generator, query_text, index, verbose)

        # Save to output file if specified
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            click.echo(f"\nResults saved to: {output}")

        # Exit with appropriate code
        sys.exit(0 if result['status'] == 'success' else 1)

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'))
        sys.exit(1)


def _execute_single_query(generator: QueryGenerator, query_text: str, index: str, verbose: bool) -> dict:
    """
    Execute a single NL query and display results.

    Args:
        generator: QueryGenerator instance
        query_text: Natural language query
        index: Target Elasticsearch index
        verbose: Show detailed output

    Returns:
        dict: Query result
    """
    click.echo(f"Processing query: {query_text}")
    click.echo(f"Target index: {index}")

    result = generator.generate_query(query_text, index)

    # Display results based on status
    if result['status'] == 'success':
        click.echo(click.style("✓ Query executed successfully", fg='green'))

        if verbose and result.get('generated_dsl'):
            click.echo("\nGenerated DSL:")
            click.echo(json.dumps(json.loads(result['generated_dsl']), indent=2))

        result_count = result.get('result_count', 0)
        click.echo(f"\nResults: {result_count} document(s) found")

        if verbose and result.get('results'):
            click.echo("\nTop results:")
            hits = result['results'].get('hits', {}).get('hits', [])
            for i, hit in enumerate(hits[:5], 1):  # Show top 5
                click.echo(f"{i}. {json.dumps(hit['_source'], indent=2)}")

    elif result['status'] == 'validation_failed':
        click.echo(click.style("✗ DSL validation failed", fg='red'))
        click.echo(f"Error: {result.get('error', 'Unknown error')}")

        if verbose and result.get('generated_dsl'):
            click.echo("\nGenerated (invalid) DSL:")
            click.echo(result['generated_dsl'])

    elif result['status'] == 'execution_failed':
        click.echo(click.style("✗ Query execution failed", fg='red'))
        click.echo(f"Error: {result.get('error', 'Unknown error')}")

    else:
        click.echo(click.style(f"✗ Query failed: {result['status']}", fg='red'))
        if result.get('error'):
            click.echo(f"Error: {result['error']}")

    return result


def _run_interactive_mode(generator: QueryGenerator, default_index: Optional[str], verbose: bool):
    """
    Run interactive REPL mode for submitting multiple queries.

    Args:
        generator: QueryGenerator instance
        default_index: Default index to use (can be overridden per query)
        verbose: Show detailed output
    """
    click.echo(click.style("\n=== MOI Elasticsearch NLP Query System - Interactive Mode ===", fg='cyan', bold=True))
    click.echo("Enter natural language queries. Type 'exit' or 'quit' to stop.\n")

    # Available indices
    available_indices = ['person_details', 'vehicle', 'violations']

    if default_index:
        click.echo(f"Default index: {default_index}")
        click.echo("You can change the index for each query.\n")

    query_count = 0

    while True:
        try:
            # Get query from user
            query_text = click.prompt(click.style("Query", fg='cyan'), type=str).strip()

            if not query_text:
                continue

            # Check for exit commands
            if query_text.lower() in ['exit', 'quit', 'q']:
                click.echo(f"\n✓ Processed {query_count} queries. Goodbye!")
                break

            # Prompt for index if not set or if user wants to change
            if default_index:
                use_default = click.confirm(f"Use default index '{default_index}'?", default=True)
                if use_default:
                    target_index = default_index
                else:
                    target_index = click.prompt(
                        "Enter index name",
                        type=click.Choice(available_indices, case_sensitive=False),
                        show_choices=True
                    )
            else:
                target_index = click.prompt(
                    "Select index",
                    type=click.Choice(available_indices, case_sensitive=False),
                    show_choices=True
                )

            # Execute query
            click.echo()  # Blank line for readability
            _execute_single_query(generator, query_text, target_index, verbose)
            click.echo()  # Blank line before next prompt

            query_count += 1

        except (KeyboardInterrupt, EOFError):
            click.echo(f"\n\n✓ Processed {query_count} queries. Goodbye!")
            break
        except Exception as e:
            click.echo(click.style(f"✗ Error: {str(e)}", fg='red'))
            click.echo("Continuing...")
            click.echo()


@cli.command()
@click.argument('queries_file', type=click.Path(exists=True))
@click.option('--index', required=True, help='Target Elasticsearch index name')
@click.option('--output', '-o', type=click.Path(), help='Save batch results to JSON Lines file')
def batch(queries_file: str, index: str, output: Optional[str]):
    """
    Process multiple queries from a file (one query per line).

    Example:
        moi-elastic-nlp batch queries.txt --index person_details -o results.jsonl
    """
    try:
        # Initialize components
        config = Config()
        logger = setup_query_translation_logger()

        es_client = ESClient(config)
        es_client.connect()

        llm_client = VLLMClient(config)

        generator = QueryGenerator(es_client, llm_client, config, logger)

        # Read queries from file
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]

        if not queries:
            click.echo("No queries found in file")
            sys.exit(1)

        click.echo(f"Processing {len(queries)} queries from {queries_file}")
        click.echo(f"Target index: {index}\n")

        # Process each query
        results = []
        success_count = 0

        with click.progressbar(queries, label='Processing queries') as bar:
            for nl_query in bar:
                result = generator.generate_query(nl_query, index)
                results.append(result)

                if result['status'] == 'success':
                    success_count += 1

        # Summary
        click.echo(f"\n✓ Processed {len(queries)} queries")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {len(queries) - success_count}")

        # Save results if output specified
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result) + '\n')
            click.echo(f"\nResults saved to: {output}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'))
        sys.exit(1)


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.option('--output', '-o', required=True, type=click.Path(), help='Output path for metrics report')
def metrics(log_file: str, output: str):
    """
    Generate baseline metrics report from query translation logs.

    Calculates:
    - DSL validity rate (% of valid JSON Query DSL)
    - Result accuracy rate (% of successful executions)
    - Latency statistics (avg LLM, ES, total)

    Example:
        moi-elastic-nlp metrics logs/query_translations.jsonl -o reports/baseline.json
    """
    try:
        click.echo(f"Analyzing logs: {log_file}")

        # Initialize metrics calculator
        calculator = MetricsCalculator()

        # Parse logs
        logs = calculator.parse_logs(log_file)

        if not logs:
            click.echo(click.style("✗ No log entries found or log file is empty", fg='yellow'))
            sys.exit(1)

        click.echo(f"Found {len(logs)} query translation(s)")

        # Generate report
        report = calculator.generate_report(logs, output)

        # Display summary
        click.echo(click.style("\n✓ Metrics Report Generated", fg='green'))
        click.echo(f"\nBaseline Metrics:")
        click.echo(f"  Corpus Size: {report['corpus_size']} queries")
        click.echo(f"  DSL Validity Rate: {report['dsl_validity_rate']:.1%}")
        click.echo(f"  Result Accuracy Rate: {report['result_accuracy_rate']:.1%}")
        click.echo(f"\nLatency Statistics:")
        click.echo(f"  Avg LLM Latency: {report['avg_llm_latency_ms']:.1f} ms")
        click.echo(f"  Avg ES Latency: {report['avg_es_latency_ms']:.1f} ms")
        click.echo(f"  Avg Total Latency: {report['avg_total_latency_ms']:.1f} ms")

        if 'queries_by_index' in report:
            click.echo(f"\nQueries by Index:")
            for idx, count in report['queries_by_index'].items():
                click.echo(f"  {idx}: {count} queries")

        click.echo(f"\nReport saved to: {output}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'))
        sys.exit(1)


if __name__ == '__main__':
    cli()
