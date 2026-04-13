"""
Multi-Index Query Executor

Executes a query plan by running steps sequentially:
  Step 1: Query index A → extract field values (e.g. prs_qid)
  Step 2: Inject extracted values into next query → query index B

This implements application-level joins since ES has no native cross-index join.
"""

import json
import logging
import time
from typing import Dict, Any, List

from src.es_client import ESClient
from src.dsl_transformer import DSLTransformer


class MultiIndexExecutor:
    """
    Executes multi-step query plans with field injection between steps.
    """

    def __init__(self, es_client: ESClient, logger: logging.Logger):
        self.es_client = es_client
        self.logger = logger
        self._transformer = DSLTransformer(logger)

    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a multi-index query plan step by step.

        Args:
            plan: Validated query plan dict with 'steps' list

        Returns:
            Result dict with status, steps_executed, final_results, total_count, latency
        """
        start_time = time.time()
        steps = plan.get('steps', [])
        step_results = {}  # step_number -> list of extracted values

        result = {
            'type': 'multi_index',
            'status': None,
            'steps_executed': [],
            'final_results': None,
            'total_count': 0,
            'error': None,
            'total_latency_ms': None,
        }

        for i, step in enumerate(steps):
            step_num = step.get('step', i + 1)
            index = step['index']
            query = step['query']
            extract_field = step.get('extract_field')
            is_last = (i == len(steps) - 1)

            # Inject values from previous steps
            query = self._inject_step_values(query, step_results)

            # Transform DSL values (e.g. nationality names → numeric codes)
            query = self._transformer._transform_node(query)

            # Bail early if injection produced an empty terms list
            # (means the previous step found no results — no point continuing)
            if self._has_empty_terms(query):
                result['status'] = 'no_results'
                result['error'] = f'Step {step_num - 1} returned no results — nothing to join on'
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                return result

            # Execute this step
            step_start = time.time()
            try:
                es_result = self.es_client.execute_query(index, {'query': query, 'size': 100})
            except Exception as e:
                result['status'] = 'execution_failed'
                result['error'] = f'Step {step_num} failed on {index}: {str(e)}'
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                return result

            step_latency = (time.time() - step_start) * 1000
            hits = es_result.get('hits', {}).get('hits', [])
            total = es_result.get('hits', {}).get('total', {}).get('value', 0)

            step_info = {
                'step': step_num,
                'index': index,
                'hit_count': total,
                'latency_ms': round(step_latency, 1),
            }

            if not is_last and extract_field:
                # Extract values for the next step's injection
                ids = self._extract_field(hits, extract_field)
                step_results[step_num] = ids
                step_info['extracted_field'] = extract_field
                step_info['extracted_count'] = len(ids)

            result['steps_executed'].append(step_info)

            # Last step: capture final results
            if is_last:
                result['final_results'] = es_result
                result['total_count'] = total
                if total == 0:
                    result['status'] = 'no_results'
                    result['error'] = 'Query plan executed successfully but no matching documents found'
                else:
                    result['status'] = 'success'

        result['total_latency_ms'] = round((time.time() - start_time) * 1000, 1)
        return result

    def _extract_field(self, hits: List[Dict], field: str) -> List[str]:
        """Extract field values from ES hits."""
        values = []
        for hit in hits:
            val = hit.get('_source', {}).get(field)
            if val is not None:
                values.append(str(val))
        return list(set(values))  # deduplicate

    def _inject_step_values(self, query: Any, step_results: Dict[int, List[str]]) -> Any:
        """
        Recursively replace "$step_N" placeholders with actual terms queries.

        Finds any string value matching "$step_N" and replaces the entire
        {"terms": {"field": "$step_N"}} with {"terms": {"field": [actual, ids]}}.
        """
        if isinstance(query, dict):
            # Check if this is a terms clause with a $step_N placeholder
            if 'terms' in query:
                terms = query['terms']
                for field, value in list(terms.items()):
                    if isinstance(value, str) and value.startswith('$step_'):
                        step_num = int(value.replace('$step_', ''))
                        ids = step_results.get(step_num, [])
                        return {'terms': {field: ids}}
            return {k: self._inject_step_values(v, step_results) for k, v in query.items()}
        elif isinstance(query, list):
            return [self._inject_step_values(item, step_results) for item in query]
        return query

    def _has_empty_terms(self, query: Any) -> bool:
        """Check if query contains an empty terms list (would match nothing)."""
        if isinstance(query, dict):
            if 'terms' in query:
                for field, value in query['terms'].items():
                    if isinstance(value, list) and len(value) == 0:
                        return True
            return any(self._has_empty_terms(v) for v in query.values())
        elif isinstance(query, list):
            return any(self._has_empty_terms(item) for item in query)
        return False
