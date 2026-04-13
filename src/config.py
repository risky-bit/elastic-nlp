"""
Configuration management for MOI Elasticsearch NLP Query System

Loads and validates environment variables from .env file.
Follows constitution principles: dependency versioning, fail-fast validation.
"""

import os
from typing import Optional
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration loaded from environment variables.

    Required variables:
    - ES_HOST: Elasticsearch host
    - ES_PORT: Elasticsearch port (converted to int)
    - ES_USER: Elasticsearch username
    - ES_PASSWORD: Elasticsearch password
    - VLLM_URL: vLLM server API base URL
    - VLLM_MODEL: Model identifier (e.g., EQuIP-Queries/EQuIP_3B)

    Optional variables with defaults:
    - LLM_TEMPERATURE: Sampling temperature (default: 0.1 for deterministic output)
    - LLM_MAX_TOKENS: Maximum response tokens (default: 500)
    - ES_INDEX_PERSON: Person details index name (default: person_details)
    - ES_INDEX_VEHICLE: Vehicle index name (default: vehicle)
    - ES_INDEX_VIOLATIONS: Violations index name (default: violations)
    """

    # Elasticsearch configuration
    ES_HOST: str = os.getenv('ES_HOST', 'localhost')
    ES_PORT: int = int(os.getenv('ES_PORT', '9200'))
    ES_USER: Optional[str] = os.getenv('ES_USER')
    ES_PASSWORD: Optional[str] = os.getenv('ES_PASSWORD')

    # vLLM Server configuration (EQuIP_3B)
    VLLM_URL: str = os.getenv('VLLM_URL', 'http://localhost:8000/v1')
    VLLM_MODEL: str = os.getenv('VLLM_MODEL', 'EQuIP-Queries/EQuIP_3B')

    # LLM parameters (for reproducibility)
    LLM_TEMPERATURE: float = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    LLM_MAX_TOKENS: int = int(os.getenv('LLM_MAX_TOKENS', '500'))

    # Elasticsearch indices (MOI data)
    ES_INDEX_PERSON: str = os.getenv('ES_INDEX_PERSON', 'person_details')
    ES_INDEX_VEHICLE: str = os.getenv('ES_INDEX_VEHICLE', 'vehicle')
    ES_INDEX_VIOLATIONS: str = os.getenv('ES_INDEX_VIOLATIONS', 'violations')

    # Prompt mode: when True, send NL query directly (matches fine-tuned LoRA training format)
    # When False (default), wrap with full prompt template + field descriptions
    USE_DIRECT_PROMPT: bool = os.getenv('USE_DIRECT_PROMPT', 'false').lower() == 'true'

    @classmethod
    def validate(cls) -> None:
        """
        Validate that all required configuration variables are present.

        Raises:
            ValueError: If any required configuration variable is missing

        Following constitution: Fail-fast at startup if configuration is invalid
        """
        missing_vars = []

        # Re-check environment variables directly (class attributes may have cached None values)
        es_user = os.getenv('ES_USER')
        es_password = os.getenv('ES_PASSWORD')

        # Check required variables
        if not es_user:
            missing_vars.append('ES_USER')
        if not es_password:
            missing_vars.append('ES_PASSWORD')

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please set them in .env file (see .env.example for template)"
            )

    @classmethod
    def get_elasticsearch_config(cls) -> dict:
        """
        Get Elasticsearch connection configuration as dict.

        Returns:
            dict: Configuration for Elasticsearch client
        """
        return {
            'hosts': [f'http://{cls.ES_HOST}:{cls.ES_PORT}'],
            'basic_auth': (cls.ES_USER, cls.ES_PASSWORD),
        }

    @classmethod
    def get_vllm_config(cls) -> dict:
        """
        Get vLLM server API configuration as dict.

        Returns:
            dict: Configuration for vLLM client
        """
        return {
            'url': cls.VLLM_URL,
            'model': cls.VLLM_MODEL,
            'temperature': cls.LLM_TEMPERATURE,
            'max_tokens': cls.LLM_MAX_TOKENS,
        }
