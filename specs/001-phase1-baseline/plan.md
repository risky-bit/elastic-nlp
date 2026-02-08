# Implementation Plan: Phase 1 Baseline - NL to Elasticsearch Query System

**Branch**: `001-phase1-baseline` | **Date**: 2026-02-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-phase1-baseline/spec.md`

## Summary

Build Phase 1 baseline system connecting natural language queries to Elasticsearch via EQuIP_3B model (LM Studio). System accepts NL input from MOI analysts, generates Elasticsearch Query DSL using LLM, validates and executes queries against person_details, vehicle, and violations indices. Measures DSL validity rate and result accuracy rate across 30-50 test queries to establish baseline for Phase 2 comparison. Target: 70% DSL validity, 70% result accuracy

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- `elasticsearch` (official Python client for Elasticsearch 8.11)
- `requests` (HTTP client for LM Studio API calls)
- `python-dotenv` (environment configuration management)
- `pytest` (testing framework)
- `pytest-docker` (Docker container management for integration tests)

**Storage**:
- Elasticsearch 8.11 (localhost:9200) - existing indices: person_details, vehicle, violations
- File-based logging (JSON structured logs for query translations)
- Local file system for prompt templates (versioned)

**Testing**: pytest with three test layers:
- Unit tests: Individual module testing (es_client, llm_client, query_generator)
- Integration tests: End-to-end NL → LLM → DSL → ES pipeline
- Contract tests: Elasticsearch index mapping validation, LM Studio API contract verification

**Target Platform**: macOS development environment, Docker for Elasticsearch
**Project Type**: Single project - Command-line application with modular Python structure

**Performance Goals**:
- End-to-end query processing: <5 seconds for 90% of simple queries
- LM Studio API response: <2 seconds (model-dependent)
- Elasticsearch query execution: <100ms p95
- Test corpus processing: 30-50 queries without crashes

**Constraints**:
- Elasticsearch 8.11 compatibility only (no 9.x features)
- LM Studio local API only (localhost:1234, no cloud LLMs)
- Single-index queries only (multi-index out of scope)
- Manual result verification for baseline (automated verification in Phase 2)

**Scale/Scope**:
- Test corpus: 30-50 MOI-specific queries
- Existing data: 100K+ documents across 3 indices
- MVP delivery: 4 user stories (3 query types + metrics measurement)
- Phase 1 only - baseline establishment for Phase 2 comparison

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Based on `.specify/memory/constitution.md`:

### I. Modular Architecture
- [x] Feature organized as self-contained module with clear boundaries
  - **es_client.py**: Elasticsearch operations only (connect, health check, get mapping, execute query)
  - **llm_client.py**: LM Studio API operations only (connect, verify model, generate DSL)
  - **query_generator.py**: Prompt construction and orchestration (no direct ES/LLM calls)
  - **metrics.py**: Performance tracking and reporting (independent module)
  - **config.py**: Environment configuration validation
- [x] No direct access to internals of other modules
  - Each module exposes clean interface (public functions only)
  - Internal helpers are module-private
- [x] Inter-module communication through well-defined interfaces
  - query_generator uses es_client.get_mapping() and llm_client.generate()
  - metrics observes via logging, doesn't modify query_generator state
- [x] Shared utilities explicitly designed for reuse
  - config.py for environment variable loading (used by all modules)
  - logger.py for structured JSON logging (used by all modules)

### II. Test-First Development (NON-NEGOTIABLE)
- [x] Tests written before implementation code
  - TDD enforced: Write test → Verify failure → Implement → Verify pass
  - Test corpus of 30-50 queries drives development
- [x] Red-Green-Refactor cycle documented in tasks
  - Tasks specify test-first order explicitly
  - Each task shows: test file → implementation file
- [x] Test strategy covers acceptance criteria from spec
  - User Story 1 scenarios → integration tests for person_details queries
  - User Story 2 scenarios → integration tests for vehicle queries
  - User Story 3 scenarios → integration tests for violations queries
  - User Story 4 scenarios → metrics report generation tests

### III. Dependency & Configuration Versioning
- [x] External model versions pinned and documented (e.g., EQuIP_3B version)
  - EQuIP_3B model version documented in README and config
  - LM Studio version recorded
- [x] LM Studio API version and configuration recorded
  - API endpoint versioned (v1)
  - Temperature, max_tokens parameters documented
- [x] Elasticsearch version compatibility declared
  - ES 8.11 explicitly required in requirements and documentation
  - No 9.x features used
- [x] Index mappings versioned and stored in repository
  - mappings/ directory stores person_details.json, vehicle.json, violations.json
  - Mappings retrieved at runtime but reference versions stored
- [x] Prompt templates versioned
  - prompts/ directory with version numbers in filenames
  - prompt_template_v1.txt as starting point
- [x] Configuration changes follow semantic versioning
  - Config schema changes documented with MAJOR.MINOR.PATCH

### IV. Reproducibility & Observability
- [x] Query translation logging designed (NL input, prompt, DSL output, ES response)
  - Every query logged to logs/query_translations.jsonl
  - Fields: timestamp, nl_query, index_mapping_hash, prompt, generated_dsl, is_valid, execution_status, result_count
- [x] LLM API parameters documented for reproducibility
  - temperature, max_tokens, model_name logged with each request
  - Enables exact reproduction of LLM behavior
- [x] Query DSL validation errors logged
  - Invalid DSL logged with error details
  - Enables prompt engineering improvements
- [x] Performance metrics tracking designed (LLM latency, ES execution time, success rate)
  - Per-query: llm_latency_ms, es_latency_ms, total_latency_ms
  - Aggregate: dsl_validity_rate, result_accuracy_rate
- [x] Connection failure logging with retry tracking
  - Connection errors logged with retry count
  - Graceful degradation without crashes
- [x] Structured logging format (JSON) planned
  - All logs in JSON Lines format (.jsonl)
  - Parsable for analysis and metrics generation

### V. Integration Testing
- [x] Integration tests planned for cross-module interactions
  - Test NL query → query_generator → es_client + llm_client → results
  - Test metrics.py consuming logs and generating reports
- [x] Elasticsearch integration tests include containerized instances
  - pytest-docker manages ES container lifecycle
  - Tests run against real Docker ES, not mocks
- [x] End-to-end NLP pipeline testing designed
  - tests/integration/test_e2e_query_pipeline.py covers full flow
  - Uses actual test corpus queries
- [x] Realistic data volumes planned for integration tests
  - Integration tests query against existing 100K+ document indices
  - Performance validated with real data

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
moi-elastic-nlp/
├── .env                    # Environment configuration (not committed)
├── .env.example            # Example environment configuration
├── .gitignore
├── requirements.txt        # Pinned dependencies with versions
├── pytest.ini              # Pytest configuration
├── README.md              # Project overview, setup instructions
│
├── src/                   # Application source code
│   ├── __init__.py
│   ├── config.py          # Environment variable loading and validation
│   ├── logger.py          # Structured JSON logging setup
│   ├── es_client.py       # Elasticsearch operations module
│   ├── llm_client.py      # LM Studio API client module
│   ├── query_generator.py # Query translation orchestration
│   ├── metrics.py         # Performance tracking and reporting
│   └── cli.py             # Command-line interface entry point
│
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures (ES container, LLM mock, test corpus)
│   ├── unit/              # Unit tests (isolated module testing)
│   │   ├── test_config.py
│   │   ├── test_es_client.py
│   │   ├── test_llm_client.py
│   │   ├── test_query_generator.py
│   │   └── test_metrics.py
│   ├── integration/       # Integration tests (multi-module, real ES)
│   │   ├── test_e2e_query_pipeline.py
│   │   ├── test_es_integration.py
│   │   └── test_metrics_integration.py
│   └── contract/          # Contract tests (ES API, LM Studio API)
│       ├── test_elasticsearch_contract.py
│       └── test_lmstudio_contract.py
│
├── data/                  # Test data and reference files
│   ├── test_corpus.json   # 30-50 MOI test queries with expected results
│   ├── mappings/          # Versioned Elasticsearch index mappings
│   │   ├── person_details.json
│   │   ├── vehicle.json
│   │   └── violations.json
│   └── prompts/           # Versioned prompt templates
│       └── prompt_template_v1.txt
│
├── logs/                  # Generated logs (gitignored)
│   ├── query_translations.jsonl
│   └── metrics.jsonl
│
├── .specify/              # Spec-Kit framework (already exists)
│   ├── memory/
│   │   └── constitution.md
│   └── templates/
│
└── specs/                 # Feature specifications (already exists)
    └── 001-phase1-baseline/
        ├── spec.md
        ├── plan.md        # This file
        ├── research.md    # Phase 0 output (to be generated)
        ├── data-model.md  # Phase 1 output (to be generated)
        └── quickstart.md  # Phase 1 output (to be generated)
```

**Structure Decision**: Single project structure selected (Option 1). This is a command-line application with clear modular boundaries. Source code organized by module responsibility (es_client, llm_client, query_generator, metrics), test organized by test type (unit, integration, contract). Configuration and data files separated from code. Follows Python best practices with src/ layout.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations detected. All gates pass.
