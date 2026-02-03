<!--
==============================================================================
SYNC IMPACT REPORT
==============================================================================
Version change: 1.1.0 → 1.2.0
Modified principles: None
Added sections:
  - Project Goals and Phases
  - Experimental methodology section
  - Decision criteria for phase transitions
Removed sections: None
Templates requiring updates:
  ✅ plan-template.md - No changes needed (gates still valid)
  ✅ spec-template.md - No changes needed
  ✅ tasks-template.md - No changes needed
Follow-up TODOs: None
Rationale: MINOR bump (1.2.0) because we're expanding project scope documentation
to include multi-phase experimental approach without changing core principles
==============================================================================
-->

# MOI Elasticsearch NLP Query System - Constitution

**Project**: Multi-phase experimental evaluation of NLP-to-Elasticsearch query approaches for MOI production deployment

## Project Goals

This project evaluates and compares different approaches to natural language query translation for Elasticsearch, specifically tailored for MOI use cases (person lookups, violations, vehicles). The goal is to identify the optimal solution through controlled experiments across multiple phases.

### Phase Structure

1. **Phase 1 - Baseline**: EQuIP_3B via LM Studio + Elasticsearch 8.15
2. **Phase 2A - Custom Wrapper**: Pre/post-processing with orchestration
3. **Phase 2B - Agent Builder**: Elastic Cloud 9.2 with Agent Builder MCP
4. **Phase 3 - Fine-tuning**: LoRA fine-tuning if needed (conditional)

### Success Metrics

- **Query DSL validity rate**: % of generated queries that are syntactically valid
- **Result accuracy rate**: % of queries that return correct results
- **Phase 1 threshold**: >70% accuracy → proceed to Phase 2
- **Phase 2 threshold**: >80% accuracy → production deployment
- **Phase 3 trigger**: <80% accuracy after Phase 2

## Core Principles

### I. Modular Architecture

Every feature must be organized as a self-contained module within the monolithic codebase.

**Rules**:
- Modules MUST have clear boundaries and single responsibility
- Modules MUST NOT directly access internals of other modules
- Inter-module communication happens through well-defined interfaces
- Shared utilities must be explicitly designed for reuse, not extraction from single-use code

**Rationale**: Modular structure within a monolith provides the benefits of isolation and maintainability without the operational complexity of microservices. Clear boundaries enable independent reasoning about components while maintaining deployment simplicity.

### II. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development is mandatory for all feature work.

**Rules**:
- Tests MUST be written before implementation code
- Tests MUST fail initially (Red phase)
- Implementation proceeds only after tests fail correctly (Green phase)
- Refactoring happens only after tests pass (Refactor phase)
- No feature is considered complete without passing tests
- Red-Green-Refactor cycle strictly enforced

**Rationale**: TDD ensures requirements are testable, provides living documentation, prevents feature creep, and creates a safety net for refactoring. The discipline catches ambiguous requirements early and builds confidence for future changes.

### III. Dependency & Configuration Versioning

All external dependencies, configurations, and system state must be versioned and tracked.

**Rules**:
- External model versions MUST be pinned and documented (e.g., EQuIP_3B model version)
- LM Studio API version and model configuration MUST be recorded
- Elasticsearch version compatibility MUST be explicitly declared (currently 8.15)
- Index mappings MUST be versioned and stored in repository
- Configuration changes MUST follow semantic versioning: MAJOR.MINOR.PATCH
  - MAJOR: Breaking changes to query format or API compatibility
  - MINOR: New query patterns, enhanced features
  - PATCH: Bug fixes, prompt refinements
- Prompt templates MUST be versioned (affects query DSL generation)

**Rationale**: Query translation systems depend on external model behavior, Elasticsearch mappings, and prompt engineering. Versioning these dependencies ensures reproducible query generation and enables debugging when model or database behavior changes.

### IV. Reproducibility & Observability

All query translations and system operations must be reproducible and observable.

**Rules**:
- Every query translation MUST be logged:
  - Input: Natural language query
  - Prompt sent to LM Studio (including index mapping context)
  - Generated: Query DSL output
  - Execution: Elasticsearch response time and result count
- LLM API calls MUST include temperature/sampling parameters for reproducibility
- Query DSL validation errors MUST be logged with the invalid DSL
- Performance metrics MUST be tracked:
  - LLM response latency
  - Elasticsearch query execution time
  - End-to-end translation time
  - Query success rate (valid DSL generated)
- Connection failures MUST be logged with retry attempts
- All logs MUST use structured format (JSON) for analysis

**Rationale**: Query translation involves two external systems (LLM and Elasticsearch) with non-deterministic behavior. Comprehensive logging enables debugging failed translations, analyzing performance bottlenecks, and improving prompt engineering. Reproducibility depends on capturing full context of each translation.

### V. Integration Testing

Features requiring cross-module interaction or external system integration must have dedicated integration tests.

**Rules**:
- Integration tests required for:
  - New module contracts
  - Changes to existing module interfaces
  - Elasticsearch query patterns and mappings
  - NLP pipeline end-to-end flows (input → processing → storage → retrieval)
  - Data ingestion and transformation pipelines
- Integration tests MUST run against realistic data volumes
- Elasticsearch integration tests MUST use containerized instances (not mocks)
- Integration test failures block feature completion

**Rationale**: Unit tests verify individual components, but NLP systems depend heavily on integration points: data pipelines, Elasticsearch queries, model serving. Integration testing catches issues in composition, data flow, and external system assumptions.

## System Constraints

### Technology Stack Requirements

**Phase 1 & 2A**:
- **Python**: 3.10+ (type hints mandatory)
- **Elasticsearch**: 8.15 (local or MOI environment)
- **LM Studio**: Local API (localhost:1234)
- **Model**: EQuIP_3B via LM Studio API
- **Dependencies**: Minimal - `elasticsearch`, `requests`, `python-dotenv` + testing/dev tools

**Phase 2B**:
- **Elastic Cloud**: 9.2 with Agent Builder
- **MCP Integration**: Agent Builder endpoint connectivity
- **Model**: EQuIP_3B connected via MCP protocol

**Phase 3** (conditional):
- **Fine-tuning**: LoRA adapters for EQuIP_3B
- **Training data**: 500-1000 MOI-specific query examples
- **Training infrastructure**: GPU environment for fine-tuning

### Experimental Methodology

- **Test corpus**: 30-50 MOI-style queries consistent across all phases
- **Query categories**: Person lookups, violations, vehicle records
- **Metrics tracking**: Valid DSL %, correct results %, latency per phase
- **Comparison baseline**: Phase 1 results serve as baseline for all improvements
- **Reproducibility**: Same queries, same Elasticsearch indices across phases

### Query Translation Quality

- Query DSL validation MUST occur before Elasticsearch execution
- Invalid DSL generation MUST be caught and reported to user with clear error messages
- Query success rate baseline: 80%+ for simple queries (match, range, bool)
- Unsupported query patterns MUST fail gracefully with helpful feedback

### Performance Standards

- LM Studio API calls: Target <2s response time (dependent on model/hardware)
- Elasticsearch queries: <100ms p95 for generated DSL execution
- End-to-end translation: Target <3s for simple queries
- Connection timeouts: 5s for Elasticsearch, 30s for LM Studio
- System MUST handle connection failures gracefully (no crashes)

### Configuration Management

- All connection details MUST use environment variables (`.env` file)
- Sensitive credentials MUST NOT be committed to repository
- Default configurations MUST be documented with example `.env.example`
- Configuration validation MUST occur at startup

## Development Workflow

### Code Review Requirements

- All changes require code review and approval
- Reviewers MUST verify constitution compliance:
  - Tests written before implementation
  - Module boundaries respected
  - Model/data versions documented
  - Integration tests cover changes
- Complexity violations require justification and documented alternatives

### Quality Gates

- All tests (unit, integration, contract) MUST pass
- Code coverage MUST be maintained or improved
- Linting and formatting checks MUST pass
- Model evaluation metrics MUST meet or exceed baseline
- Constitution compliance checklist MUST be completed

### Query Pattern Development Workflow

1. Identify query pattern requirements (e.g., "range queries", "bool with filters")
2. Define test cases with expected Query DSL output
3. Write failing tests (TDD)
4. Implement prompt engineering or DSL generation logic
5. Verify tests pass
6. Document query pattern in supported patterns list
7. Add example to test suite

### Prompt Engineering Workflow

1. Document current prompt template version
2. Identify translation failures or improvement opportunities
3. Create test cases for problematic queries
4. Experiment with prompt variations (track all versions)
5. Measure success rate improvement
6. Update prompt template with version bump
7. Document changes and rationale

## Governance

### Amendment Process

- Constitution supersedes all other development practices
- Amendments require:
  1. Documented rationale for change
  2. Team review and approval
  3. Migration plan for affected code
  4. Version bump following semantic versioning
- Breaking changes (principle removal/redefinition) increment MAJOR version
- New principles or expanded guidance increment MINOR version
- Clarifications and wording improvements increment PATCH version

### Compliance Review

- All pull requests MUST verify constitution compliance
- Feature planning MUST include constitution check gate
- Quarterly review of constitution effectiveness
- Violations require documented justification or must be resolved

### Version History

- Changes to this document MUST update the version and amendment date
- Sync Impact Report MUST be generated for each amendment
- Dependent templates and artifacts MUST be updated to maintain consistency

**Version**: 1.2.0 | **Ratified**: 2026-02-03 | **Last Amended**: 2026-02-03
