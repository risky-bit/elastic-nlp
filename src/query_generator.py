"""
Query Generator for NL to Elasticsearch Query DSL Translation

Orchestrates the complete query generation pipeline:
1. Load index mapping from Elasticsearch
2. Construct prompt with template + mapping + NL query
3. Generate DSL via LLM client
4. Validate generated DSL
5. Execute query on Elasticsearch
6. Log complete translation for metrics
"""

import json
import time
import hashlib
import logging
import requests
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from elasticsearch.exceptions import ConnectionError as ESConnectionError, TransportError

from src.es_client import ESClient
from src.llm_client import VLLMClient
from src.config import Config


class QueryGenerator:
    """
    Orchestrates NL query → Elasticsearch Query DSL translation

    Following constitution: Modular architecture (I), Test-First Development (II)
    """

    def __init__(
        self,
        es_client: ESClient,
        llm_client: VLLMClient,
        config: Config,
        logger: logging.Logger
    ):
        """
        Initialize QueryGenerator with required dependencies

        Args:
            es_client: Elasticsearch client for index operations
            llm_client: LLM client for DSL generation
            config: Configuration object
            logger: Python logging.Logger instance for reproducibility
        """
        self.es_client = es_client
        self.llm_client = llm_client
        self.config = config
        self.logger = logger
        self.prompt_template: Optional[str] = None

    def load_prompt_template(self, template_path: str) -> str:
        """
        Load prompt template from file

        Args:
            template_path: Path to prompt template file

        Returns:
            str: Prompt template content

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        self.prompt_template = template
        return template

    def construct_prompt(self, nl_query: str, index_mapping: Dict[str, Any]) -> str:
        """
        Construct full prompt from template, mapping, and NL query

        Args:
            nl_query: Natural language query from user
            index_mapping: Elasticsearch index mapping dictionary

        Returns:
            str: Complete prompt ready for LLM

        Following constitution: Reproducibility (IV) - structured prompt construction
        """
        # Load default template if not already loaded
        if self.prompt_template is None:
            template_path = Path(__file__).parent.parent / 'data' / 'prompts' / 'prompt_template_v1.txt'
            self.load_prompt_template(str(template_path))

        # Format mapping as readable JSON
        mapping_json = json.dumps(index_mapping, indent=2)

        # Fill template placeholders
        prompt = self.prompt_template.replace('{mapping}', mapping_json)
        prompt = prompt.replace('{query}', nl_query)

        return prompt

    def validate_dsl(self, dsl_string: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate generated DSL for JSON syntax and basic structure

        Args:
            dsl_string: Generated DSL string from LLM

        Returns:
            Tuple of (is_valid, parsed_dsl, error_message)
            - is_valid: True if DSL is valid
            - parsed_dsl: Parsed JSON dict if valid, None otherwise
            - error_message: Error description if invalid, None otherwise

        Following constitution: Test-First Development (II) - validation before execution
        """
        # Check for empty or None input
        if not dsl_string or not dsl_string.strip():
            return False, None, "Generated DSL is empty"

        # Try to parse JSON
        try:
            parsed_dsl = json.loads(dsl_string)
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON syntax: {str(e)}"

        # Check for root "query" key
        if not isinstance(parsed_dsl, dict):
            return False, None, "DSL must be a JSON object"

        if 'query' not in parsed_dsl:
            return False, None, "DSL must contain a root 'query' key"

        # Basic structure validation passed
        return True, parsed_dsl, None

    def generate_query(
        self,
        nl_query: str,
        index_name: str
    ) -> Dict[str, Any]:
        """
        Generate and execute Elasticsearch query from natural language

        Complete pipeline:
        1. Get index mapping from ES
        2. Construct prompt
        3. Generate DSL via LLM
        4. Validate DSL
        5. Execute query on ES
        6. Log complete translation

        Args:
            nl_query: Natural language query from user
            index_name: Target Elasticsearch index name

        Returns:
            dict: Result dictionary with status, results, and metadata

        Following constitution: Reproducibility (IV) - complete logging for baseline metrics
        """
        start_time = time.time()

        # Initialize result dictionary
        result = {
            'nl_query': nl_query,
            'index_name': index_name,
            'status': None,
            'generated_dsl': None,
            'is_valid_json': False,
            'results': None,
            'error': None,
            'llm_latency_ms': None,
            'es_latency_ms': None,
            'total_latency_ms': None
        }

        try:
            # Step 1: Get index mapping (with ES connection error handling)
            try:
                mapping_response = self.es_client.get_mapping(index_name)
            except ESConnectionError as e:
                result['status'] = 'es_connection_failed'
                result['error'] = (
                    f"Cannot connect to Elasticsearch at {self.config.ES_HOST}:{self.config.ES_PORT}. "
                    f"Please ensure Elasticsearch is running and accessible. Error: {str(e)}"
                )
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                self._log_translation(result, None, None)
                return result
            except TransportError as e:
                result['status'] = 'es_transport_error'
                result['error'] = f"Elasticsearch transport error: {str(e)}"
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                self._log_translation(result, None, None)
                return result

            # Extract mapping for the specific index
            if index_name in mapping_response:
                index_mapping = mapping_response[index_name]
            else:
                # If response structure is different, use the whole response
                index_mapping = mapping_response

            # Calculate mapping hash for versioning
            mapping_json = json.dumps(index_mapping, sort_keys=True)
            mapping_hash = hashlib.md5(mapping_json.encode()).hexdigest()[:8]

            # Step 2: Construct prompt
            prompt = self.construct_prompt(nl_query, index_mapping)

            # Step 3: Generate DSL via LLM (with vLLM connection error handling)
            llm_start = time.time()
            try:
                generated_dsl = self.llm_client.generate_dsl(
                    prompt,
                    temperature=self.config.LLM_TEMPERATURE,
                    max_tokens=self.config.LLM_MAX_TOKENS
                )
                llm_latency = (time.time() - llm_start) * 1000  # Convert to milliseconds
            except requests.exceptions.ConnectionError as e:
                result['status'] = 'llm_connection_failed'
                result['error'] = (
                    f"Cannot connect to vLLM at {self.config.VLLM_URL}. "
                    f"Please ensure vLLM server is running (e.g., via Docker Compose). "
                    f"Error: {str(e)}"
                )
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                self._log_translation(result, prompt, mapping_hash)
                return result
            except requests.exceptions.Timeout as e:
                result['status'] = 'llm_timeout'
                result['error'] = (
                    f"vLLM request timed out after {self.llm_client.timeout}s. "
                    f"The model may be overloaded or the query is too complex. Error: {str(e)}"
                )
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                self._log_translation(result, prompt, mapping_hash)
                return result
            except requests.exceptions.RequestException as e:
                result['status'] = 'llm_request_failed'
                result['error'] = f"vLLM request failed: {str(e)}"
                result['total_latency_ms'] = (time.time() - start_time) * 1000
                self._log_translation(result, prompt, mapping_hash)
                return result

            result['generated_dsl'] = generated_dsl
            result['llm_latency_ms'] = llm_latency

            # Step 4: Validate DSL
            is_valid, parsed_dsl, validation_error = self.validate_dsl(generated_dsl)
            result['is_valid_json'] = is_valid

            if not is_valid:
                result['status'] = 'validation_failed'
                result['error'] = validation_error
                result['total_latency_ms'] = (time.time() - start_time) * 1000

                # Log failed translation
                self._log_translation(result, prompt, mapping_hash)
                return result

            # Step 5: Execute query on Elasticsearch
            es_start = time.time()
            try:
                search_results = self.es_client.execute_query(index_name, parsed_dsl)
                es_latency = (time.time() - es_start) * 1000

                result['results'] = search_results
                result['es_latency_ms'] = es_latency
                result['status'] = 'success'
                result['result_count'] = search_results.get('hits', {}).get('total', {}).get('value', 0)

            except ESConnectionError as es_error:
                result['status'] = 'es_connection_failed'
                result['error'] = (
                    f"Lost connection to Elasticsearch during query execution. "
                    f"Error: {str(es_error)}"
                )
            except TransportError as es_error:
                result['status'] = 'es_transport_error'
                result['error'] = f"Elasticsearch transport error during execution: {str(es_error)}"
            except Exception as es_error:
                result['status'] = 'execution_failed'
                result['error'] = f"Elasticsearch execution error: {str(es_error)}"

        except Exception as e:
            result['status'] = 'pipeline_error'
            result['error'] = f"Pipeline error: {str(e)}"

        # Calculate total latency
        result['total_latency_ms'] = (time.time() - start_time) * 1000

        # Step 6: Log complete translation for metrics
        self._log_translation(
            result,
            prompt if 'prompt' in locals() else None,
            mapping_hash if 'mapping_hash' in locals() else None
        )

        return result

    def _log_translation(
        self,
        result: Dict[str, Any],
        prompt: Optional[str],
        mapping_hash: Optional[str]
    ):
        """
        Log query translation for metrics calculation

        Args:
            result: Result dictionary from generate_query
            prompt: Full prompt sent to LLM
            mapping_hash: Hash of index mapping for versioning

        Following constitution: Reproducibility (IV) - structured logging
        """
        log_entry = {
            'nl_query': result['nl_query'],
            'index_name': result['index_name'],
            'index_mapping_hash': mapping_hash,
            'prompt': prompt,
            'generated_dsl': result['generated_dsl'],
            'is_valid_json': result['is_valid_json'],
            'execution_status': result['status'],
            'result_count': result.get('result_count'),
            'llm_latency_ms': result['llm_latency_ms'],
            'es_latency_ms': result.get('es_latency_ms'),
            'total_latency_ms': result['total_latency_ms'],
            'llm_model': self.config.VLLM_MODEL,
            'llm_temperature': self.config.LLM_TEMPERATURE,
        }

        # Add error if present
        if result.get('error'):
            log_entry['error'] = result['error']

        self.logger.info('Query translation', extra=log_entry)
