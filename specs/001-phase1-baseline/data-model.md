# Data Model: Phase 1 Baseline NL-to-Elasticsearch Query System

**Date**: 2026-02-03
**Feature**: Phase 1 Baseline - NL to Elasticsearch Query System
**Branch**: 001-phase1-baseline

## Overview

This document defines the key data structures and entities used in the Phase 1 baseline system. All entities are designed to support TDD implementation, reproducibility (constitution principle IV), and metrics tracking.

---

## Core Entities

### 1. QueryRequest

Represents a natural language query submitted by the user.

**Fields**:
- `query_text` (str): Natural language query from user (e.g., "Find all Qatari nationals in Doha")
- `target_index` (str): Target Elasticsearch index name (person_details, vehicle, or violations)
- `timestamp` (str): ISO 8601 timestamp of query submission
- `request_id` (str): Unique identifier (UUID4) for tracking and correlation

**Validation Rules**:
- `query_text` must not be empty
- `target_index` must be one of: person_details, vehicle, violations
- `timestamp` must be valid ISO 8601 format
- `request_id` must be valid UUID4

**Relationships**:
- One QueryRequest → One QueryTranslation
- One QueryRequest → One QueryResult (if executed successfully)

**Example**:
```python
{
    "query_text": "Find person named Ahmed Al-Mansoori",
    "target_index": "person_details",
    "timestamp": "2026-02-03T14:30:45.123Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 2. IndexMapping

Elasticsearch index schema retrieved for prompt context.

**Fields**:
- `index_name` (str): Name of the ES index
- `mapping_json` (dict): Complete mapping structure from ES
- `mapping_hash` (str): MD5 hash of mapping_json for versioning
- `retrieved_at` (str): ISO 8601 timestamp when mapping was fetched
- `es_version` (str): Elasticsearch version (e.g., "8.11.0")

**Validation Rules**:
- `index_name` must match actual ES index
- `mapping_json` must be valid JSON dict
- `mapping_hash` must be 32-character MD5 hex
- `es_version` must match "8.11.x" format

**Relationships**:
- One IndexMapping → Many QueryTranslations (reused across queries)
- Cached in memory for session duration

**Example**:
```python
{
    "index_name": "person_details",
    "mapping_json": {
        "properties": {
            "name": {"type": "text"},
            "nationality": {"type": "keyword"},
            "age": {"type": "integer"}
        }
    },
    "mapping_hash": "a1b2c3d4e5f6...",
    "retrieved_at": "2026-02-03T14:00:00Z",
    "es_version": "8.11.0"
}
```

---

### 3. PromptTemplate

Versioned template for LLM prompts.

**Fields**:
- `template_id` (str): Version identifier (e.g., "prompt_template_v1")
- `template_text` (str): Full prompt template with {placeholders}
- `placeholders` (list[str]): List of required placeholder names
- `version` (str): Semantic version (e.g., "1.0.0")
- `created_at` (str): ISO 8601 timestamp of template creation

**Validation Rules**:
- `template_text` must contain all placeholders in `placeholders` list
- `version` must follow semver format (MAJOR.MINOR.PATCH)
- Placeholders: {mapping_json}, {user_query} (required for v1)

**State Transitions**:
- v1.0.0 → v1.1.0 (minor improvements, backward compatible)
- v1.x.x → v2.0.0 (breaking changes to prompt structure)

**Example**:
```python
{
    "template_id": "prompt_template_v1",
    "template_text": "You are an Elasticsearch Query DSL expert...\\n\\nIndex Mapping:\\n{mapping_json}\\n\\nNatural Language Query:\\n{user_query}\\n\\nOutput only valid Elasticsearch Query DSL JSON:",
    "placeholders": ["mapping_json", "user_query"],
    "version": "1.0.0",
    "created_at": "2026-02-03T12:00:00Z"
}
```

---

### 4. LLMRequest

Request sent to LM Studio API.

**Fields**:
- `request_id` (str): Correlates with QueryRequest.request_id
- `model_name` (str): LLM model identifier (e.g., "EQuIP_3B")
- `prompt` (str): Full constructed prompt (template filled with mapping + query)
- `temperature` (float): Sampling temperature (0.1-0.3 for deterministic output)
- `max_tokens` (int): Maximum response tokens (500 for Query DSL)
- `sent_at` (str): ISO 8601 timestamp when request sent

**Validation Rules**:
- `temperature` must be between 0.0 and 1.0
- `max_tokens` must be positive integer
- `prompt` must not be empty
- `model_name` must match configured LM Studio model

**Relationships**:
- One LLMRequest → One LLMResponse

**Example**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "model_name": "EQuIP_3B",
    "prompt": "<full_prompt_text>",
    "temperature": 0.1,
    "max_tokens": 500,
    "sent_at": "2026-02-03T14:30:45.200Z"
}
```

---

### 5. LLMResponse

Response received from LM Studio API.

**Fields**:
- `request_id` (str): Correlates with LLMRequest.request_id
- `generated_text` (str): Raw text output from LLM
- `response_time_ms` (int): LLM API latency in milliseconds
- `received_at` (str): ISO 8601 timestamp when response received
- `model_info` (dict): Model metadata from API response (if available)

**Validation Rules**:
- `generated_text` must not be None (can be empty on error)
- `response_time_ms` must be non-negative
- If `response_time_ms` > 30000, warning logged (timeout threshold)

**Relationships**:
- One LLMResponse → One QueryDSL (after parsing)

**Example**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "generated_text": '{"query": {"match": {"name": "Ahmed"}}}',
    "response_time_ms": 1250,
    "received_at": "2026-02-03T14:30:46.450Z",
    "model_info": {"model": "EQuIP_3B", "tokens_used": 145}
}
```

---

### 6. QueryDSL

Parsed and validated Elasticsearch Query DSL.

**Fields**:
- `request_id` (str): Correlates with QueryRequest.request_id
- `dsl_json` (dict): Parsed Query DSL as Python dict
- `is_valid_json` (bool): Whether generated_text is valid JSON
- `is_valid_dsl` (bool): Whether DSL passes Elasticsearch validation (optional, can be None if not executed)
- `validation_error` (str | None): Error message if validation failed
- `validated_at` (str): ISO 8601 timestamp when validation performed

**Validation Rules**:
- `dsl_json` must be valid JSON dict (if `is_valid_json` is True)
- If `is_valid_json` is False, `validation_error` must be set
- `is_valid_dsl` determined by executing against ES (or None if not executed)

**Relationships**:
- One QueryDSL → One ESQueryExecution (if valid and executed)

**Example (valid)**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "dsl_json": {"query": {"match": {"name": "Ahmed"}}},
    "is_valid_json": True,
    "is_valid_dsl": True,
    "validation_error": None,
    "validated_at": "2026-02-03T14:30:46.500Z"
}
```

**Example (invalid JSON)**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "dsl_json": None,
    "is_valid_json": False,
    "is_valid_dsl": None,
    "validation_error": "JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2",
    "validated_at": "2026-02-03T14:30:46.500Z"
}
```

---

### 7. ESQueryExecution

Elasticsearch query execution details.

**Fields**:
- `request_id` (str): Correlates with QueryRequest.request_id
- `index_name` (str): ES index queried
- `dsl_json` (dict): Query DSL executed
- `execution_time_ms` (int): ES query execution time in milliseconds
- `result_count` (int): Number of results returned
- `execution_status` (str): success | error
- `error_message` (str | None): Error details if execution_status == error
- `executed_at` (str): ISO 8601 timestamp when query executed

**Validation Rules**:
- `execution_time_ms` must be non-negative
- `result_count` must be non-negative
- `execution_status` must be "success" or "error"
- If `execution_status` == "error", `error_message` must be set

**Relationships**:
- One ESQueryExecution → One QueryResult

**Example (success)**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "index_name": "person_details",
    "dsl_json": {"query": {"match": {"name": "Ahmed"}}},
    "execution_time_ms": 45,
    "result_count": 3,
    "execution_status": "success",
    "error_message": None,
    "executed_at": "2026-02-03T14:30:46.600Z"
}
```

**Example (error)**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "index_name": "person_details",
    "dsl_json": {"query": {"match": {"invalid_field": "Ahmed"}}},
    "execution_time_ms": 0,
    "result_count": 0,
    "execution_status": "error",
    "error_message": "RequestError(400, 'search_phase_execution_exception', 'no such field [invalid_field]')",
    "executed_at": "2026-02-03T14:30:46.600Z"
}
```

---

### 8. QueryResult

Final result returned to user.

**Fields**:
- `request_id` (str): Correlates with QueryRequest.request_id
- `query_text` (str): Original NL query (for user context)
- `result_hits` (list[dict]): ES results (simplified, top N hits)
- `total_hits` (int): Total number of matching documents
- `query_successful` (bool): Overall success status
- `error_summary` (str | None): User-friendly error message if failed

**Validation Rules**:
- `total_hits` must match len(result_hits) or exceed it (if paginated)
- If `query_successful` is False, `error_summary` must be set
- `result_hits` limited to top 10 by default (configurable)

**Relationships**:
- One QueryResult per QueryRequest

**Example (success)**:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "query_text": "Find person named Ahmed Al-Mansoori",
    "result_hits": [
        {"_id": "1", "_source": {"name": "Ahmed Al-Mansoori", "age": 35}},
        {"_id": "2", "_source": {"name": "Ahmed Al-Mansoori", "age": 42}}
    ],
    "total_hits": 2,
    "query_successful": True,
    "error_summary": None
}
```

---

### 9. QueryTranslationLog

Complete log entry for reproducibility (constitution principle IV).

**Fields**:
- `timestamp` (str): ISO 8601 timestamp
- `request_id` (str): Unique query identifier
- `nl_query` (str): Natural language input
- `index_name` (str): Target ES index
- `index_mapping_hash` (str): MD5 hash of ES mapping used
- `prompt` (str): Full prompt sent to LLM
- `llm_model` (str): LLM model name
- `llm_temperature` (float): LLM temperature parameter
- `llm_max_tokens` (int): LLM max tokens parameter
- `generated_dsl` (str): Raw LLM output
- `is_valid_json` (bool): DSL JSON validity
- `execution_status` (str): success | error | not_executed
- `result_count` (int | None): ES result count (if executed)
- `llm_latency_ms` (int): LLM response time
- `es_latency_ms` (int | None): ES execution time (if executed)
- `total_latency_ms` (int): End-to-end time
- `error_details` (str | None): Error message if failed

**Storage**: Appended to `logs/query_translations.jsonl` (JSON Lines format)

**Relationships**:
- Aggregates data from: QueryRequest, LLMRequest, LLMResponse, QueryDSL, ESQueryExecution

**Example**:
```json
{
  "timestamp": "2026-02-03T14:30:46.650Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "nl_query": "Find person named Ahmed Al-Mansoori",
  "index_name": "person_details",
  "index_mapping_hash": "a1b2c3d4e5f6...",
  "prompt": "<full_prompt_text>",
  "llm_model": "EQuIP_3B",
  "llm_temperature": 0.1,
  "llm_max_tokens": 500,
  "generated_dsl": "{\"query\": {\"match\": {\"name\": \"Ahmed\"}}}",
  "is_valid_json": true,
  "execution_status": "success",
  "result_count": 2,
  "llm_latency_ms": 1250,
  "es_latency_ms": 45,
  "total_latency_ms": 1350,
  "error_details": null
}
```

---

### 10. TestCorpusQuery

Test query from the 30-50 query test corpus.

**Fields**:
- `query_id` (str): Unique identifier (e.g., "TC001")
- `query_text` (str): Natural language query
- `target_index` (str): Target ES index
- `query_category` (str): person_lookup | vehicle_search | violations_query
- `expected_dsl_pattern` (str | None): Expected Query DSL structure (optional, for validation)
- `expected_result_count_min` (int | None): Minimum expected results (optional)
- `notes` (str | None): Additional context or edge case description

**Validation Rules**:
- `query_id` must be unique across corpus
- `query_category` must be one of: person_lookup, vehicle_search, violations_query
- `target_index` must match query_category (person_details, vehicle, violations)

**Storage**: `data/test_corpus.json` (array of TestCorpusQuery objects)

**Example**:
```python
{
    "query_id": "TC001",
    "query_text": "Find person named Ahmed Al-Mansoori",
    "target_index": "person_details",
    "query_category": "person_lookup",
    "expected_dsl_pattern": "match query on name field",
    "expected_result_count_min": 1,
    "notes": "Basic match query test case"
}
```

---

### 11. MetricsReport

Aggregate metrics summary for baseline measurement.

**Fields**:
- `report_id` (str): Unique report identifier (UUID4)
- `generated_at` (str): ISO 8601 timestamp
- `corpus_size` (int): Total test queries processed
- `dsl_validity_rate` (float): Percentage of queries generating valid JSON DSL (0.0-1.0)
- `result_accuracy_rate` (float): Percentage of queries returning correct results (0.0-1.0, manual verification)
- `avg_llm_latency_ms` (float): Average LLM response time
- `avg_es_latency_ms` (float): Average ES execution time
- `avg_total_latency_ms` (float): Average end-to-end time
- `queries_by_category` (dict): Breakdown by query category
- `failure_summary` (dict): Common failure patterns

**Validation Rules**:
- `dsl_validity_rate` and `result_accuracy_rate` must be between 0.0 and 1.0
- `corpus_size` must match number of queries in test corpus
- Averages must be non-negative

**Relationships**:
- One MetricsReport per test run
- Derived from analyzing all QueryTranslationLog entries

**Example**:
```python
{
    "report_id": "report-2026-02-03-run1",
    "generated_at": "2026-02-03T15:00:00Z",
    "corpus_size": 50,
    "dsl_validity_rate": 0.74,  # 37/50 queries
    "result_accuracy_rate": 0.72,  # 36/50 queries (manually verified)
    "avg_llm_latency_ms": 1450.5,
    "avg_es_latency_ms": 52.3,
    "avg_total_latency_ms": 1550.2,
    "queries_by_category": {
        "person_lookup": {"total": 20, "valid_dsl": 16, "accurate": 15},
        "vehicle_search": {"total": 15, "valid_dsl": 12, "accurate": 11},
        "violations_query": {"total": 15, "valid_dsl": 9, "accurate": 10}
    },
    "failure_summary": {
        "invalid_json": 13,  # 13 queries generated invalid JSON
        "field_not_found": 8,  # 8 queries used non-existent fields
        "incorrect_results": 14  # 14 queries returned wrong results
    }
}
```

---

## Entity Relationships Diagram

```
QueryRequest (1) ---> (1) IndexMapping [retrieved for context]
                |
                +--> (1) PromptTemplate [filled with mapping + query]
                |
                +--> (1) LLMRequest ---> (1) LLMResponse
                                              |
                                              v
                QueryDSL <---[parsed from]--- (validation)
                    |
                    +--> (0..1) ESQueryExecution
                                      |
                                      v
                                QueryResult

QueryTranslationLog [aggregates all above entities for logging]

TestCorpusQuery (many) --[drives]--> QueryRequest (many)

MetricsReport [analyzes]--> QueryTranslationLog (many)
```

---

## Data Flow

1. **User submits QueryRequest** → System retrieves IndexMapping
2. **PromptTemplate filled** with mapping + query → LLMRequest created
3. **LLMRequest sent** → LLMResponse received
4. **LLMResponse parsed** → QueryDSL validated
5. **QueryDSL executed** (if valid) → ESQueryExecution performed
6. **ESQueryExecution results** → QueryResult returned to user
7. **QueryTranslationLog written** to logs/query_translations.jsonl
8. **Test corpus processed** → Multiple QueryRequests → Multiple QueryTranslationLogs
9. **MetricsReport generated** from analyzing all QueryTranslationLogs

---

## Constitution Alignment

All entities designed to support:

✅ **Modular Architecture** (Principle I): Clear entity boundaries, no cross-entity dependencies
✅ **Test-First Development** (Principle II): TestCorpusQuery drives TDD implementation
✅ **Dependency Versioning** (Principle III): PromptTemplate has version field, IndexMapping has hash
✅ **Reproducibility & Observability** (Principle IV): QueryTranslationLog captures complete context
✅ **Integration Testing** (Principle V): TestCorpusQuery enables realistic integration tests

---

## Implementation Notes

- All entities use Python dataclasses or Pydantic models (TBD in tasks phase)
- JSON serialization required for logging (all entities JSON-serializable)
- Type hints mandatory for all fields (Python 3.10+ compatibility)
- Validation logic implemented in entity constructors or validators
- Entity relationships enforced via request_id correlation (not database foreign keys)
