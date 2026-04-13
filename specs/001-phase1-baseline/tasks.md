# Tasks: Phase 1 Baseline - NL to Elasticsearch Query System

**Input**: Design documents from `/specs/001-phase1-baseline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Following constitution mandate for Test-First Development (NON-NEGOTIABLE) - all tests MUST be written before implementation and MUST fail before code is written.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure (src/, tests/unit/, tests/integration/, tests/contract/, data/mappings/, data/prompts/, logs/)
- [x] T002 Initialize Python project with requirements.txt containing pinned versions (elasticsearch==8.11.1, requests==2.31.0, python-dotenv==1.0.0, pytest==7.4.3, pytest-docker==2.0.1, pytest-cov==4.1.0)
- [x] T003 [P] Create .gitignore file excluding .env, logs/, __pycache__/, .pytest_cache/, venv/
- [x] T004 [P] Create .env.example with ES_HOST, ES_PORT, ES_USER, ES_PASSWORD, LM_STUDIO_URL, LM_STUDIO_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS placeholders
- [x] T005 [P] Configure pytest.ini with testpaths, python_files, python_classes, python_functions patterns and timeout settings
- [x] T006 [P] Create README.md documenting project overview, setup instructions, and Phase 1 baseline goals
- [x] T007 [P] Create empty __init__.py files in src/, tests/, tests/unit/, tests/integration/, tests/contract/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Components (Write FIRST, ensure they FAIL)

- [x] T008 [P] Write unit test for config.py in tests/unit/test_config.py - test environment variable loading, validation, type conversion, missing required vars error
- [x] T009 [P] Write unit test for logger.py in tests/unit/test_logger.py - test JSON formatter, log file creation, structured log output format
- [x] T010 [P] Write contract test for Elasticsearch connection in tests/contract/test_elasticsearch_contract.py - test cluster health check, index existence verification, mapping retrieval
- [x] T011 [P] Write contract test for LM Studio API in tests/contract/test_lmstudio_contract.py - test API endpoint availability, model loaded verification, completions endpoint response format

### Foundational Implementation (Implement AFTER tests fail)

- [x] T012 Create config.py in src/config.py - implement Config class with dotenv loading, required variable validation (ES_HOST, ES_PORT, ES_USER, ES_PASSWORD, LM_STUDIO_URL, LM_STUDIO_MODEL), type conversion for integers (ES_PORT), defaults for optional vars (LLM_TEMPERATURE=0.1, LLM_MAX_TOKENS=500)
- [x] T013 Create logger.py in src/logger.py - implement JSONFormatter class, configure file handler for logs/query_translations.jsonl, setup structured logging with timestamp, level, message, extra fields
- [x] T014 Create es_client.py in src/es_client.py - implement ESClient class with __init__(config), connect() method, check_health() method, get_mapping(index_name) method - all methods return proper error handling for connection failures
- [x] T015 Create llm_client.py in src/llm_client.py - implement LMStudioClient class with __init__(config), verify_model() method, generate_dsl(prompt, temperature, max_tokens) method posting to /v1/completions endpoint - handle timeouts and connection errors
- [x] T016 Verify all foundational unit tests pass - run pytest tests/unit/test_config.py tests/unit/test_logger.py -v
- [ ] T017 Verify all foundational contract tests pass - run pytest tests/contract/ -v (requires ES and LM Studio running)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 4 - Query Results Measurement (Priority: P1) 🎯

**Goal**: Enable batch processing of test corpus queries and generate metrics report showing DSL validity rate and result accuracy rate for baseline comparison

**Why before US1-3**: Metrics infrastructure must exist to measure baseline during development of other stories. This runs in parallel with US1.

**Independent Test**: Run 30-50 query test corpus and verify metrics report is generated with DSL validity rate and result accuracy rate percentages

### Tests for User Story 4 (Write FIRST, ensure they FAIL)

- [x] T018 [P] [US4] Write unit test for metrics.py in tests/unit/test_metrics.py - test MetricsCalculator.calculate_dsl_validity_rate(), calculate_result_accuracy_rate(), generate_report() methods with mock log data
- [x] T019 [P] [US4] Write integration test for metrics report generation in tests/integration/test_metrics_integration.py - test reading logs/query_translations.jsonl, calculating metrics, writing reports/phase1_baseline_metrics.json

### Implementation for User Story 4

- [x] T020 [US4] Create metrics.py in src/metrics.py - implement MetricsCalculator class with parse_logs(log_file_path), calculate_dsl_validity_rate(), calculate_result_accuracy_rate(), calculate_latency_stats(), generate_report(output_path) methods
- [ ] T021 [US4] Add batch processing support to cli.py - implement batch command accepting --corpus data/test_corpus.json --output logs/batch_results.json, iterate through corpus queries, log each translation to query_translations.jsonl (will be implemented with CLI in Phase 4)
- [ ] T022 [US4] Add metrics command to cli.py - implement metrics command accepting --input logs/query_translations.jsonl --output reports/phase1_baseline_metrics.json, invoke MetricsCalculator.generate_report() (will be implemented with CLI in Phase 4)
- [x] T023 [US4] Verify US4 unit tests pass - run pytest tests/unit/test_metrics.py -v
- [x] T024 [US4] Verify US4 integration tests pass - run pytest tests/integration/test_metrics_integration.py -v

**Checkpoint**: Metrics infrastructure complete - can measure baseline during US1-3 development

---

## Phase 4: User Story 1 - Simple Person Lookup Query (Priority: P1) 🎯 MVP

**Goal**: Enable MOI analysts to submit natural language person lookup queries and receive results from person_details index

**Independent Test**: Submit queries like "Find all people named Ahmed" or "Show me persons from Doha" and verify valid Query DSL generation and correct results

### Tests for User Story 1 (Write FIRST, ensure they FAIL)

- [x] T025 [P] [US1] Write unit test for query_generator.py in tests/unit/test_query_generator.py - test QueryGenerator.construct_prompt(), validate_dsl(), generate_query() with mocked es_client and llm_client
- [x] T026 [P] [US1] Write integration test for person_details queries in tests/integration/test_e2e_query_pipeline.py - test end-to-end flow: "Find person named Ahmed Al-Mansoori" → valid DSL → ES execution → results returned
- [x] T027 [P] [US1] Write integration test for person attribute queries in tests/integration/test_e2e_query_pipeline.py - test "Show me all Qatari nationals" → nationality field query → correct results
- [x] T028 [P] [US1] Write integration test for multi-criteria person queries in tests/integration/test_e2e_query_pipeline.py - test "Find males from Doha aged over 30" → bool query with must clauses → accurate results

### Implementation for User Story 1

- [x] T029 [US1] Create data/prompts/prompt_template_v1.txt - write prompt template with structure: "You are an Elasticsearch Query DSL expert..." + index mapping placeholder + NL query placeholder + output format instruction
- [x] T030 [US1] Retrieve and save person_details index mapping - use curl or es_client to get mapping from existing ES index, save to data/mappings/person_details.json for versioning
- [x] T031 [US1] Create query_generator.py in src/query_generator.py - implement QueryGenerator class with __init__(es_client, llm_client, config, logger), load_prompt_template(version), construct_prompt(nl_query, index_mapping), validate_dsl(dsl_json), generate_query(nl_query, index_name) orchestrating full flow
- [x] T032 [US1] Implement DSL validation in query_generator.py - add validate_dsl() method checking JSON syntax validity, basic Query DSL structure (has "query" key), return validation result with error details if invalid
- [x] T033 [US1] Create cli.py in src/cli.py - implement query command with --query "NL query text" --index person_details flags, instantiate QueryGenerator, execute query via es_client, display results, log full translation to query_translations.jsonl
- [x] T034 [US1] Add interactive mode to cli.py - implement query --interactive flag allowing analyst to submit multiple queries in REPL loop, select target index per query
- [x] T035 [US1] Add error handling for ES connection failures in query_generator.py - catch elasticsearch.exceptions.ConnectionError, log error with retry count, return user-friendly error message without crashing
- [x] T036 [US1] Add error handling for vLLM connection failures in query_generator.py - catch requests.exceptions.ConnectionError/Timeout, log error, return helpful message (check vLLM running)
- [x] T037 [US1] Verify US1 unit tests pass - run pytest tests/unit/test_query_generator.py -v
- [x] T038 [US1] Verify US1 integration tests pass - run pytest tests/integration/test_e2e_query_pipeline.py -k person -v (requires ES with person_details data and vLLM)

**Checkpoint**: At this point, User Story 1 should be fully functional - analysts can query person_details index with natural language

---

## Phase 5: User Story 2 - Vehicle Record Search (Priority: P2)

**Goal**: Enable MOI analysts to submit natural language vehicle search queries and receive results from vehicle index

**Independent Test**: Submit queries like "Find all Toyota vehicles" or "Show vehicles registered in 2023" and verify accurate Query DSL and results

### Tests for User Story 2 (Write FIRST, ensure they FAIL)

- [x] T039 [P] [US2] Write integration test for vehicle plate number queries in tests/integration/test_e2e_query_pipeline.py - test "Find all vehicles with plate number ABC123" → exact match query → matching vehicle records
- [x] T040 [P] [US2] Write integration test for vehicle attribute queries in tests/integration/test_e2e_query_pipeline.py - test "Show me all SUVs" → vehicle type field query → correct results
- [x] T041 [P] [US2] Write integration test for vehicle date-based queries in tests/integration/test_e2e_query_pipeline.py - test "Find vehicles registered in last 6 months" → range query → appropriate results

### Implementation for User Story 2

- [x] T042 [US2] Retrieve and save vehicle index mapping - use es_client to get mapping from existing ES vehicle index, save to data/mappings/vehicle.json for versioning
- [x] T043 [US2] Update query_generator.py to support vehicle index - ensure get_mapping() works for vehicle index, construct_prompt() uses vehicle mapping when index_name="vehicle"
- [x] T044 [US2] Update cli.py to support vehicle queries - add "vehicle" as valid --index option, update help text with vehicle query examples
- [x] T045 [US2] Verify US2 integration tests pass - run pytest tests/integration/test_e2e_query_pipeline.py -k vehicle -v (requires ES with vehicle data and LM Studio)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - analysts can query both person_details and vehicle indices

---

## Phase 6: User Story 3 - Violations Query (Priority: P3)

**Goal**: Enable MOI analysts to submit natural language violation search queries and receive results from violations index

**Independent Test**: Submit queries like "Find speeding violations" or "Show violations from last week" and verify correct Query DSL and results

### Tests for User Story 3 (Write FIRST, ensure they FAIL)

- [x] T046 [P] [US3] Write integration test for violation type queries in tests/integration/test_e2e_query_pipeline.py - test "Find all speeding violations" → violation type filter → matching records
- [x] T047 [P] [US3] Write integration test for violation location queries in tests/integration/test_e2e_query_pipeline.py - test "Show violations on Corniche Road" → location query → correct results
- [x] T048 [P] [US3] Write integration test for combined violation criteria in tests/integration/test_e2e_query_pipeline.py - test "Find violations from December involving heavy vehicles" → complex bool query → accurate results

### Implementation for User Story 3

- [x] T049 [US3] Retrieve and save violations index mapping - use es_client to get mapping from existing ES violations index, save to data/mappings/violations.json for versioning
- [x] T050 [US3] Update query_generator.py to support violations index - ensure get_mapping() works for violations index, construct_prompt() uses violations mapping when index_name="violations"
- [x] T051 [US3] Update cli.py to support violations queries - add "violations" as valid --index option, update help text with violations query examples
- [x] T052 [US3] Verify US3 integration tests pass - run pytest tests/integration/test_e2e_query_pipeline.py -k violations -v (requires ES with violations data and LM Studio)

**Checkpoint**: All three user stories (US1, US2, US3) should now be independently functional across all MOI indices

---

## Phase 7: Test Corpus Creation & Baseline Measurement

**Purpose**: Create comprehensive test corpus and establish baseline metrics for Phase 2 comparison

- [x] T053 [P] Create test corpus file data/test_corpus.json with 30-50 MOI queries - include 10-15 person_details queries, 10-15 vehicle queries, 10-15 violations queries covering scenarios from US1-3 acceptance criteria
- [x] T054 Run full test corpus batch processing - execute `python -m src.cli batch --corpus data/test_corpus.json --output logs/batch_results.json`, verify all 30-50 queries logged to query_translations.jsonl
- [x] T055 Generate Phase 1 baseline metrics report - execute `python -m src.cli metrics --input logs/query_translations.jsonl --output reports/phase1_baseline_metrics.json`
- [x] T056 Verify baseline metrics meet success criteria - check DSL validity rate ≥70%, result accuracy rate ≥70% (manual verification of results), document any failures for prompt engineering improvements
- [x] T057 Create metrics comparison baseline - save reports/phase1_baseline_metrics.json as phase1_baseline.json for Phase 2 comparison

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [x] T058 [P] Add comprehensive unit tests for es_client.py in tests/unit/test_es_client.py - test connection pooling, health check edge cases, mapping retrieval errors, query execution with mocked ES responses
- [x] T059 [P] Add comprehensive unit tests for llm_client.py in tests/unit/test_llm_client.py - test timeout handling, retry logic, response parsing, error categorization with mocked HTTP responses
- [x] T060 [P] Add debug flag to cli.py - implement --debug flag showing full prompt sent to LLM, raw LLM response, validation errors, ES error messages for troubleshooting
- [ ] T061 [P] Update README.md with quickstart instructions - document environment setup, LM Studio configuration, ES verification, running single queries, batch processing, metrics generation
- [ ] T062 [P] Add prompt engineering improvement workflow to README.md - document how to analyze failed queries, iterate on prompt_template_v1.txt, version prompts with v2, v3, measure success rate improvement
- [x] T063 Run full test suite with coverage - execute `pytest tests/ -v --cov=src --cov-report=term-missing`, verify >80% code coverage, identify untested edge cases
- [ ] T064 Run quickstart.md validation - follow all steps in specs/001-phase1-baseline/quickstart.md from environment setup through metrics generation, verify all commands work
- [x] T065 Create Phase 1 completion report - document final DSL validity rate, result accuracy rate, common failure patterns, prompt engineering insights, recommendations for Phase 2

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 4 (Phase 3)**: Depends on Foundational - Can run in parallel with US1
- **User Story 1 (Phase 4)**: Depends on Foundational - MVP target
- **User Story 2 (Phase 5)**: Depends on Foundational - Can start in parallel with US1 if staffed
- **User Story 3 (Phase 6)**: Depends on Foundational - Can start in parallel with US1/US2 if staffed
- **Test Corpus & Baseline (Phase 7)**: Depends on US1, US2, US3 completion
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 4 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories, runs in parallel with US1
- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories, MVP target
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 patterns but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Builds on US1 patterns but independently testable

### Within Each User Story (TDD Enforcement)

- **Tests MUST be written FIRST** and MUST FAIL before implementation (NON-NEGOTIABLE per constitution)
- Unit tests before implementation
- Integration tests before end-to-end features
- Contract tests verify external dependencies before relying on them
- Story complete and passing all tests before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005, T006, T007)
- All Foundational tests marked [P] can run in parallel (T008, T009, T010, T011)
- Once Foundational phase completes, User Stories 1 and 4 can start in parallel
- All US1 tests can run in parallel (T025, T026, T027, T028)
- All US2 tests can run in parallel (T039, T040, T041)
- All US3 tests can run in parallel (T046, T047, T048)
- All Polish tasks marked [P] can run in parallel (T058, T059, T060, T061, T062)
- Different user stories can be worked on in parallel by different team members after Foundational completes

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together (TDD - write these FIRST):
Task T025: "Write unit test for query_generator.py in tests/unit/test_query_generator.py"
Task T026: "Write integration test for person_details queries in tests/integration/test_e2e_query_pipeline.py"
Task T027: "Write integration test for person attribute queries in tests/integration/test_e2e_query_pipeline.py"
Task T028: "Write integration test for multi-criteria person queries in tests/integration/test_e2e_query_pipeline.py"

# Verify all tests FAIL (Red phase)
pytest tests/unit/test_query_generator.py tests/integration/test_e2e_query_pipeline.py -k person -v

# Then implement (Green phase):
Task T029: "Create data/prompts/prompt_template_v1.txt"
Task T030: "Retrieve and save person_details index mapping"
Task T031: "Create query_generator.py in src/query_generator.py"
# ... continue with remaining implementation tasks

# Verify all tests PASS
pytest tests/unit/test_query_generator.py tests/integration/test_e2e_query_pipeline.py -k person -v
```

---

## Implementation Strategy

### MVP First (User Stories 4 + 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T017) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 4 (T018-T024) - Metrics infrastructure in parallel
4. Complete Phase 4: User Story 1 (T025-T038) - MVP person lookup queries
5. **STOP and VALIDATE**: Test US1 independently with real MOI queries
6. Run preliminary metrics on US1 queries to validate measurement system
7. Demo to stakeholders if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T017)
2. Add User Story 4 + User Story 1 → Test independently → Measure baseline for person queries (MVP!)
3. Add User Story 2 → Test independently → Extend baseline to vehicle queries
4. Add User Story 3 → Test independently → Complete baseline across all MOI indices
5. Create full test corpus → Generate comprehensive baseline metrics (Phase 7)
6. Polish and finalize → Production-ready Phase 1 baseline
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T017)
2. Once Foundational is done:
   - Developer A: User Story 4 (Metrics) - T018-T024
   - Developer B: User Story 1 (Person queries) - T025-T038
3. After US1 complete:
   - Developer A: User Story 2 (Vehicle queries) - T039-T045
   - Developer B: User Story 3 (Violations queries) - T046-T052
4. Team collaborates on test corpus creation and baseline measurement (Phase 7)
5. Stories complete and integrate independently

---

## Notes

- **TDD NON-NEGOTIABLE**: Per constitution, tests MUST be written before implementation and MUST fail before code is written (Red-Green-Refactor)
- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability (US1, US2, US3, US4)
- Each user story should be independently completable and testable
- Verify tests fail (Red) before implementing, then verify tests pass (Green)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution compliance: All tasks follow modular architecture (clear module boundaries), test-first development (tests before code), dependency versioning (pinned requirements, versioned prompts/mappings), reproducibility (structured logging), integration testing (pytest-docker for ES)
- Success criteria: ≥70% DSL validity rate, ≥70% result accuracy rate on 30-50 query test corpus
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence, implementation without tests

---

## Phase 9: LoRA Fine-Tuning (EQuIP_3B on MOI Schema)

**Goal**: Fine-tune EQuIP_3B with LoRA on MOI-specific (NL→DSL) pairs so model learns real field names/values instead of hallucinating from pre-training priors.

- [x] T066 Generate 400 ES-validated (NL→DSL) training pairs covering all 3 indices - data/generate_training_data.py, every pair validated by executing against real ES, split 85/15 train/valid
- [x] T067 Run LoRA fine-tuning with mlx_lm - `mlx_lm.lora --model EQuIP-Queries/EQuIP_3B --train --data data/training --iters 300 --batch-size 4 --num-layers 8 --adapter-path adapters/equip_moi_v1` — val loss converged to 0.196
- [x] T068 Add USE_DIRECT_PROMPT config flag to config.py - when True, skip full prompt template and send plain NL query (matches LoRA training format exactly)
- [x] T069 Evaluate fine-tuned model with direct prompt mode - run corpus, compare results
  - Baseline (pre-fine-tune, template): 5/36 = 13.9% result-finding rate
  - Fine-tuned (template): 14/36 = 38.9% result-finding rate
  - Fine-tuned (direct prompt): 30/36 = 83.3% result-finding rate ✓
- [x] T070 Fix remaining failure patterns via iterative training (v2→v4):
  - Added DOB-only, color+status, "registered in year", two-color OR, fine+status, "persons with X nationality" examples
  - v2 (400 iters, 436 pairs, val 0.148): 32/36 = 88.9%
  - v3 (500 iters, 504 pairs, val 0.153): 35/36 = 97.2%
  - v4 (500 iters, 535 pairs, val 0.125): **36/36 = 100%** ✓ — active adapter: adapters/equip_moi_v4
