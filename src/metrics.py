"""
Metrics calculation for MOI Elasticsearch NLP Query System

Calculates baseline metrics: DSL validity rate, result accuracy rate, latency statistics.
Follows constitution principles: reproducibility, observability, performance tracking.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional


class MetricsCalculator:
    """
    Calculate baseline metrics from query translation logs.

    Metrics calculated:
    - DSL Validity Rate: % of queries generating syntactically valid Query DSL
    - Result Accuracy Rate: % of queries returning correct results
    - Latency Statistics: Average LLM, ES, and total latency

    Following constitution: Performance tracking designed (IV. Reproducibility & Observability)
    """

    def parse_logs(self, log_file_path: str) -> List[Dict[str, Any]]:
        """
        Parse query translation logs from JSON Lines file.

        Args:
            log_file_path: Path to logs/query_translations.jsonl

        Returns:
            List of log entries as dictionaries

        Following constitution: Structured logging format (JSON Lines) for analysis
        """
        logs = []

        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except FileNotFoundError:
            return []

        return logs

    def calculate_dsl_validity_rate(self, logs: List[Dict[str, Any]]) -> float:
        """
        Calculate percentage of queries generating valid Query DSL.

        Args:
            logs: List of query translation log entries

        Returns:
            float: DSL validity rate (0.0 to 1.0)

        Following constitution: DSL validity rate metric (Success Criteria SC-002)
        """
        if not logs:
            return 0.0

        valid_count = sum(1 for log in logs if log.get('is_valid_json', False))
        total_count = len(logs)

        return valid_count / total_count

    def calculate_result_accuracy_rate(self, logs: List[Dict[str, Any]]) -> float:
        """
        Calculate percentage of queries returning correct results.

        Args:
            logs: List of query translation log entries

        Returns:
            float: Result accuracy rate (0.0 to 1.0)

        Following constitution: Result accuracy rate metric (Success Criteria SC-003)
        """
        if not logs:
            return 0.0

        # Count queries with successful execution and results found
        # 'no_results' = DSL valid + executed OK, just no matching data — not a model failure
        success_count = sum(1 for log in logs if log.get('status') in ('success', 'no_results') or log.get('execution_status') == 'success')
        total_count = len(logs)

        return success_count / total_count

    def calculate_latency_stats(self, logs: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate average latency statistics.

        Args:
            logs: List of query translation log entries

        Returns:
            dict: Latency statistics with avg_llm_latency_ms, avg_es_latency_ms, avg_total_latency_ms

        Following constitution: Performance metrics tracking (latency)
        """
        if not logs:
            return {
                'avg_llm_latency_ms': 0.0,
                'avg_es_latency_ms': 0.0,
                'avg_total_latency_ms': 0.0,
            }

        # Calculate LLM latency (only queries where LLM ran)
        llm_latencies = [log['llm_latency_ms'] for log in logs if log.get('llm_latency_ms') is not None]
        avg_llm = sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0.0

        # Calculate ES latency (only successful queries have this)
        es_latencies = [log['es_latency_ms'] for log in logs if log.get('es_latency_ms') is not None]
        avg_es = sum(es_latencies) / len(es_latencies) if es_latencies else 0.0

        # Calculate total latency (only queries with a recorded total)
        total_latencies = [log['total_latency_ms'] for log in logs if log.get('total_latency_ms') is not None]
        avg_total = sum(total_latencies) / len(total_latencies) if total_latencies else 0.0

        return {
            'avg_llm_latency_ms': avg_llm,
            'avg_es_latency_ms': avg_es,
            'avg_total_latency_ms': avg_total,
        }

    def generate_report(self, logs: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
        """
        Generate comprehensive metrics report from logs.

        Args:
            logs: List of query translation log entries
            output_path: Path to save metrics report JSON

        Returns:
            dict: Generated metrics report

        Following constitution: Baseline metrics documented for Phase 2 comparison (SC-007)
        """
        # Calculate metrics
        dsl_validity = self.calculate_dsl_validity_rate(logs)
        result_accuracy = self.calculate_result_accuracy_rate(logs)
        latency_stats = self.calculate_latency_stats(logs)

        # Generate report
        report = {
            'report_id': str(uuid.uuid4()),
            'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'corpus_size': len(logs),
            'dsl_validity_rate': dsl_validity,
            'result_accuracy_rate': result_accuracy,
            'avg_llm_latency_ms': latency_stats['avg_llm_latency_ms'],
            'avg_es_latency_ms': latency_stats['avg_es_latency_ms'],
            'avg_total_latency_ms': latency_stats['avg_total_latency_ms'],
        }

        # Optionally add query breakdown by index
        if logs:
            queries_by_index = {}
            for log in logs:
                index_name = log.get('index_name', 'unknown')
                if index_name not in queries_by_index:
                    queries_by_index[index_name] = 0
                queries_by_index[index_name] += 1

            report['queries_by_index'] = queries_by_index

        # Write report to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        return report
