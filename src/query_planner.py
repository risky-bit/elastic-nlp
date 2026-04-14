"""
Multi-Index Query Planner

Detects whether a natural language query spans multiple indices and generates
a query plan — a sequence of ES queries with field extraction and injection
between steps.

Query plan format:
{
  "type": "multi_index",
  "steps": [
    {
      "step": 1,
      "index": "moi-gp-all-profiles-details-v1",
      "query": {"term": {"person_natcde": "634"}},
      "extract_field": "prs_qid"
    },
    {
      "step": 2,
      "index": "moi-violations-v1",
      "query": {
        "bool": {
          "must": [
            {"terms": {"VLN_OWNQID": "$step_1"}},
            {"term": {"VLN_TYPE": "SPEEDING"}}
          ]
        }
      }
    }
  ]
}

$step_N is replaced at runtime with the extracted field values from step N.
"""

import json
import logging
import requests
from typing import Dict, Any, Tuple, Optional

from src.llm_client import VLLMClient
from src.config import Config


# Keywords that indicate a multi-index (join) query
MULTI_INDEX_SIGNALS = [
    # Person → Violations
    'violations for', 'violations by', 'violations of',
    'fines for', 'fines by', 'fines of',
    # Person → Vehicle
    'vehicles owned by', 'vehicles belonging to', 'vehicles of',
    'cars owned by', 'cars belonging to',
    # General cross-entity signals
    'owned by', 'belonging to', 'registered to',
    'who have violations', 'who have fines',
    'with violations', 'with fines',
    "their violations", "their vehicles", "their cars",
]


class MultiIndexQueryPlanner:
    """
    Detects multi-index queries and generates query plans for cross-index joins.
    """

    # Index join field mapping
    JOIN_FIELDS = {
        ('moi-gp-all-profiles-details-v1', 'moi-violations-v1'): ('prs_qid', 'VLN_OWNQID'),
        ('moi-gp-all-profiles-details-v1', 'moi-vehicle-info-v1'): ('prs_qid', 'VRG_OWNQID'),
    }

    def __init__(self, llm_client: VLLMClient, config: Config, logger: logging.Logger):
        self.llm_client = llm_client
        self.config = config
        self.logger = logger

    def is_multi_index(self, nl_query: str) -> bool:
        """
        Detect whether a query requires a cross-index join.

        Checks for natural language signals that imply joining person data
        with violations or vehicle data.
        """
        query_lower = nl_query.lower()
        return any(signal in query_lower for signal in MULTI_INDEX_SIGNALS)

    def plan(self, nl_query: str) -> Dict[str, Any]:
        """
        Generate a multi-index query plan from a natural language query.

        Calls LLM with the plain NL query (matching training format),
        parses and returns the query plan JSON.

        Returns:
            dict with keys: type, steps — or error dict on failure
        """
        try:
            raw = self.llm_client.generate_dsl(
                nl_query,
                temperature=self.config.LLM_TEMPERATURE,
                max_tokens=self.config.LLM_MAX_TOKENS,
                timeout=120
            )
        except requests.exceptions.RequestException as e:
            return {'error': f'LLM request failed: {str(e)}'}

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError as e:
            return {'error': f'Invalid JSON from LLM: {str(e)}', 'raw': raw}

        return {'status': 'success', 'plan': plan}

    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a query plan has the required structure.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(plan, dict):
            return False, 'Plan must be a JSON object'

        if plan.get('error'):
            return False, plan['error']

        if plan.get('type') != 'multi_index':
            return False, f"Plan type must be 'multi_index', got: {plan.get('type')}"

        steps = plan.get('steps')
        if not isinstance(steps, list) or len(steps) < 2:
            return False, 'Plan must have at least 2 steps'

        for i, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                return False, f'Step {i} must be an object'
            if 'index' not in step:
                return False, f'Step {i} missing required field: index'
            if 'query' not in step:
                return False, f'Step {i} missing required field: query'
            # All steps except the last must have extract_field
            if i < len(steps) and 'extract_field' not in step:
                return False, f'Step {i} missing required field: extract_field'

        return True, None
