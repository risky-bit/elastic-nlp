# Phase 0 Research: Phase 1 Baseline NL-to-Elasticsearch Query System

**Date**: 2026-02-03
**Feature**: Phase 1 Baseline - NL to Elasticsearch Query System
**Branch**: 001-phase1-baseline

## Research Overview

All technical decisions are specified in plan.md with no NEEDS CLARIFICATION markers. This research focuses on best practices for the chosen technology stack to ensure high-quality, maintainable implementation following TDD principles.

## Research Areas

### 1. Elasticsearch Python Client Best Practices

**Decision**: Use official `elasticsearch` Python client (8.x series for ES 8.11 compatibility)

**Best Practices Identified**:
- Connection management: Use connection pooling with `Elasticsearch()` client instance (singleton pattern)
- Health checks: Always verify cluster health before accepting queries (`client.cluster.health()`)
- Index mapping retrieval: Use `client.indices.get_mapping(index=name)` for schema discovery
- Query execution: Use `client.search(index=name, body=query_dsl)` for Query DSL execution
- Error handling: Catch `elasticsearch.exceptions.ConnectionError` and `elasticsearch.exceptions.RequestError` separately
- Timeout configuration: Set explicit timeouts (5s default per constitution)
- Type hints: Use `elasticsearch.Elasticsearch` type for client instances

**Rationale**: Official client provides robust connection management, comprehensive error handling, and ES 8.x compatibility. Type hints improve IDE support and catch errors early.

**Alternatives Considered**:
- `elasticsearch-dsl-py`: Higher-level abstraction, but adds unnecessary complexity for our use case
- Direct HTTP requests via `requests`: Lower-level control, but requires manual retry logic and connection pooling

**References**:
- Elasticsearch Python Client documentation (8.x series)
- Connection pooling patterns for production systems

---

### 2. LM Studio API Integration Patterns

**Decision**: Use `requests` library for HTTP calls to LM Studio local API (localhost:1234/v1/completions)

**Best Practices Identified**:
- API endpoint: `/v1/completions` (OpenAI-compatible endpoint)
- Request format: JSON payload with `model`, `prompt`, `temperature`, `max_tokens` fields
- Response parsing: Extract `choices[0].text` from JSON response
- Timeout handling: 30-second timeout per constitution (model inference can be slow)
- Retry logic: Single retry on connection failure, fail fast on model errors
- Parameter logging: Log `temperature` and `max_tokens` for reproducibility
- Error categorization: Distinguish connection errors (retry) from model errors (fail)

**Rationale**: `requests` is lightweight, well-tested, and sufficient for simple HTTP API calls. LM Studio uses OpenAI-compatible API format which is well-documented.

**Alternatives Considered**:
- `httpx`: Async support not needed for Phase 1 (sequential query processing)
- `openai` Python SDK: Unnecessary dependency when using local LM Studio

**API Contract Example**:
```python
POST http://localhost:1234/v1/completions
Content-Type: application/json

{
  "model": "EQuIP_3B",
  "prompt": "<index_mapping>\n\n<user_query>",
  "temperature": 0.1,
  "max_tokens": 500
}
```

**References**:
- LM Studio API documentation
- OpenAI API compatibility spec

---

### 3. Prompt Engineering for Query DSL Generation

**Decision**: Template-based prompting with index mapping context + NL query

**Best Practices Identified**:
- Prompt structure: System context + Index mapping (JSON) + User query + Output format instruction
- Temperature setting: Low temperature (0.1-0.3) for deterministic Query DSL generation
- Max tokens: 500 tokens sufficient for most Query DSL responses
- Output format instruction: Explicitly request JSON output with no explanatory text
- Prompt versioning: Store prompts in `data/prompts/prompt_template_v{N}.txt` with version numbers
- Schema versioning: Track which prompt version works with which ES version

**Prompt Template v1 Structure**:
```
You are an Elasticsearch Query DSL expert. Given the following Elasticsearch index mapping and a natural language query, generate ONLY the Query DSL JSON (no explanations).

Index Mapping:
{mapping_json}

Natural Language Query:
{user_query}

Output only valid Elasticsearch Query DSL JSON:
```

**Rationale**: Providing index mapping gives LLM schema context for field names and types. Low temperature reduces hallucination. Explicit output format instruction reduces post-processing complexity.

**References**:
- Prompt engineering best practices for code generation
- Few-shot learning patterns (may be added in Phase 2)

---

### 4. Python Testing with pytest and Docker

**Decision**: Use `pytest` with `pytest-docker` plugin for containerized Elasticsearch testing

**Best Practices Identified**:
- Test structure: Separate unit/integration/contract tests in distinct directories
- Fixtures: Use `conftest.py` for shared fixtures (ES container, test corpus)
- Docker management: `pytest-docker` handles ES container lifecycle automatically
- Test isolation: Each integration test uses fresh ES indices or cleans up after
- Parametrized tests: Use `@pytest.mark.parametrize` for test corpus queries
- Mocking: Mock LLM responses in unit tests, use real LLM in integration tests (if available)
- Coverage: Aim for >80% code coverage, but prioritize meaningful tests over coverage percentage

**pytest-docker Setup**:
```python
# conftest.py
import pytest
from pytest_docker.plugin import Services

@pytest.fixture(scope="session")
def elasticsearch_container(docker_services):
    """Start Elasticsearch container for integration tests"""
    docker_services.start("elasticsearch")
    docker_services.wait_for_service("elasticsearch", 9200)
    yield docker_services
    docker_services.stop("elasticsearch")
```

**Rationale**: Docker ensures consistent test environment matching production ES version. pytest-docker automates container lifecycle. Parametrized tests enable test corpus-driven development.

**References**:
- pytest documentation (fixtures, parametrization)
- pytest-docker plugin documentation
- Docker Compose for Elasticsearch 8.11

---

### 5. Structured Logging with Python logging module

**Decision**: Use Python's built-in `logging` module configured for JSON output

**Best Practices Identified**:
- Log format: JSON Lines (.jsonl) for machine-readable logs
- Log levels: INFO for query translations, ERROR for failures, DEBUG for detailed tracing
- Log fields (per query):
  - timestamp (ISO 8601)
  - nl_query (natural language input)
  - index_name (target ES index)
  - index_mapping_hash (MD5 hash of mapping for versioning)
  - prompt (full prompt sent to LLM)
  - generated_dsl (LLM output)
  - is_valid_json (boolean - DSL validation result)
  - execution_status (success/error)
  - result_count (number of ES results)
  - llm_latency_ms (LLM API response time)
  - es_latency_ms (ES query execution time)
  - total_latency_ms (end-to-end)
- Log rotation: Not needed for Phase 1 (single test run), add in Phase 2
- Log storage: `logs/query_translations.jsonl` (gitignored)

**Logger Configuration**:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            **record.__dict__.get("extra", {})
        }
        return json.dumps(log_data)

logger = logging.getLogger("query_translation")
handler = logging.FileHandler("logs/query_translations.jsonl")
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

**Rationale**: JSON Lines format enables easy parsing for metrics analysis. Structured logs are machine-readable and support Phase 2 automated analysis. Python's built-in logging is battle-tested.

**References**:
- Python logging documentation
- JSON Lines specification (jsonlines.org)
- Structured logging best practices

---

### 6. Environment Configuration with python-dotenv

**Decision**: Use `python-dotenv` for `.env` file loading with `config.py` validation layer

**Best Practices Identified**:
- `.env` file structure: KEY=VALUE pairs, one per line
- `.env.example`: Committed template with placeholder values
- `.env`: Gitignored actual values (never commit credentials)
- Validation: `config.py` validates all required vars present at startup
- Type conversion: Convert string env vars to appropriate types (int for ports, bool for flags)
- Defaults: Provide sensible defaults for non-sensitive values (localhost, standard ports)
- Error handling: Fail fast at startup if required config missing

**Environment Variables**:
```bash
# .env.example
ES_HOST=localhost
ES_PORT=9200
ES_USER=elastic
ES_PASSWORD=changeme
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=EQuIP_3B
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=500
```

**config.py Validation**:
```python
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    ES_HOST = os.getenv("ES_HOST", "localhost")
    ES_PORT = int(os.getenv("ES_PORT", "9200"))
    ES_USER = os.getenv("ES_USER")  # Required, no default
    ES_PASSWORD = os.getenv("ES_PASSWORD")  # Required, no default

    @classmethod
    def validate(cls):
        if not cls.ES_USER or not cls.ES_PASSWORD:
            raise ValueError("ES_USER and ES_PASSWORD must be set")
```

**Rationale**: `.env` files prevent hardcoding credentials. Validation at startup catches configuration errors early. Example file documents required configuration for new developers.

**References**:
- python-dotenv documentation
- Twelve-Factor App methodology (config section)

---

## Summary

All technology choices are concrete and validated against constitution requirements:

✅ **Modular Architecture**: Clear module boundaries (es_client, llm_client, query_generator, metrics)
✅ **Test-First Development**: pytest with unit/integration/contract test layers, test corpus-driven
✅ **Dependency Versioning**: requirements.txt pins all versions, prompt templates versioned
✅ **Reproducibility**: JSON structured logging captures all query context, LLM parameters logged
✅ **Integration Testing**: pytest-docker for containerized ES, end-to-end pipeline tests

**No NEEDS CLARIFICATION items remain** - ready to proceed to Phase 1 (Design).

**Key Decisions Made**:
1. Python 3.10+ with type hints
2. Official `elasticsearch` client (8.x)
3. `requests` for LM Studio API
4. `pytest` + `pytest-docker` for testing
5. JSON Lines structured logging
6. `python-dotenv` for configuration
7. Template-based prompting with low temperature (0.1-0.3)
8. Single project structure (src/ + tests/)

**Next Phase**: Generate data-model.md defining Query, Log, and Metrics entities based on these technical decisions.
