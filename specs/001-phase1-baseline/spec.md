# Feature Specification: Phase 1 Baseline - NL to Elasticsearch Query System

**Feature Branch**: `001-phase1-baseline`
**Created**: 2026-02-03
**Status**: Draft
**Input**: User description: "Phase 1 Baseline: Build NL-to-DSL query system connecting EQuIP_3B (via LM Studio at localhost:1234) to Elasticsearch 8.11 (localhost:9200), test with 30-50 MOI queries across person_details, violations, and vehicle indices, measure DSL validity rate and result accuracy rate to establish baseline for Phase 2 comparison"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simple Person Lookup Query (Priority: P1)

An MOI analyst needs to find person records using natural language queries instead of writing complex Elasticsearch Query DSL manually.

**Why this priority**: This is the most common query pattern for MOI operations. Delivering this first provides immediate value and allows analysts to test the system with real workflows.

**Independent Test**: Can be fully tested by submitting queries like "Find all people named Ahmed" or "Show me persons from Doha" and verifying the system generates valid Query DSL and returns correct results from person_details index.

**Acceptance Scenarios**:

1. **Given** the system is connected to Elasticsearch and LM Studio, **When** analyst enters "Find person named Ahmed Al-Mansoori", **Then** system generates valid Query DSL match query, executes it against person_details index, and returns matching records
2. **Given** a query about person attributes, **When** analyst enters "Show me all Qatari nationals", **Then** system generates appropriate Query DSL for nationality field and returns correct results
3. **Given** multiple search criteria, **When** analyst enters "Find males from Doha aged over 30", **Then** system generates bool query with multiple must clauses and returns accurate results

---

### User Story 2 - Vehicle Record Search (Priority: P2)

An MOI analyst needs to search vehicle records using natural language to investigate traffic violations or ownership.

**Why this priority**: Vehicle queries are the second most common use case. This extends the baseline to multi-index support and different data structures.

**Independent Test**: Can be fully tested by submitting queries like "Find all Toyota vehicles" or "Show vehicles registered in 2023" and verifying accurate Query DSL generation and result retrieval from vehicle index.

**Acceptance Scenarios**:

1. **Given** connection to vehicle index, **When** analyst enters "Find all vehicles with plate number ABC123", **Then** system generates exact match query and returns matching vehicle records
2. **Given** vehicle attribute query, **When** analyst enters "Show me all SUVs", **Then** system generates appropriate query for vehicle type field and returns correct results
3. **Given** date-based query, **When** analyst enters "Find vehicles registered in last 6 months", **Then** system generates range query and returns appropriate results

---

### User Story 3 - Violations Query (Priority: P3)

An MOI analyst needs to search traffic violation records using natural language to analyze patterns or investigate specific incidents.

**Why this priority**: Violations queries complete the three main MOI data categories. This validates the system works across different index schemas.

**Independent Test**: Can be fully tested by submitting queries like "Find speeding violations" or "Show violations from last week" and verifying correct Query DSL and results from violations index.

**Acceptance Scenarios**:

1. **Given** connection to violations index, **When** analyst enters "Find all speeding violations", **Then** system generates query filtering by violation type and returns matching records
2. **Given** location-based query, **When** analyst enters "Show violations on Corniche Road", **Then** system generates appropriate location query and returns correct results
3. **Given** combined criteria, **When** analyst enters "Find violations from December involving heavy vehicles", **Then** system generates complex bool query and returns accurate results

---

### User Story 4 - Query Results Measurement (Priority: P1)

The development team needs to measure baseline performance metrics to compare against Phase 2 improvements.

**Why this priority**: Without measurement, we cannot determine if Phase 2 improvements are effective. This runs in parallel with P1-P3 user stories.

**Independent Test**: Can be fully tested by running the 30-50 query test corpus and generating metrics report showing DSL validity rate and result accuracy rate.

**Acceptance Scenarios**:

1. **Given** a test corpus of 30-50 MOI queries, **When** system processes all queries, **Then** system logs each query with validity status (valid/invalid DSL) and accuracy status (correct/incorrect results)
2. **Given** completed test run, **When** analyst requests metrics report, **Then** system calculates and displays DSL validity rate percentage and result accuracy rate percentage
3. **Given** baseline metrics, **When** metrics are saved, **Then** results are stored in format that allows comparison with Phase 2 outcomes

---

### Edge Cases

- What happens when user submits query with ambiguous terms (e.g., "Find Ahmed" without specifying field)?
- How does system handle queries requesting fields that don't exist in the index?
- What happens when Elasticsearch connection fails during query execution?
- How does system respond when LM Studio generates malformed Query DSL?
- What happens when query returns zero results - is it a system error or valid empty result?
- How does system handle queries mixing multiple indices (e.g., "Find person Ahmed and their violations")?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST connect to Elasticsearch instance at localhost:9200 and verify cluster health before accepting queries
- **FR-002**: System MUST connect to LM Studio API at localhost:1234 and verify model availability
- **FR-003**: System MUST accept natural language queries as text input from user
- **FR-004**: System MUST retrieve index mapping from Elasticsearch for target index (person_details, vehicle, or violations)
- **FR-005**: System MUST construct prompt containing index mapping and user's natural language query
- **FR-006**: System MUST send prompt to LM Studio API and receive generated Query DSL as response
- **FR-007**: System MUST validate generated Query DSL is syntactically correct JSON before execution
- **FR-008**: System MUST execute validated Query DSL against appropriate Elasticsearch index
- **FR-009**: System MUST return query results to user in readable format
- **FR-010**: System MUST log each query translation with input query, generated DSL, validation status, execution status, and result count
- **FR-011**: System MUST handle connection failures to Elasticsearch gracefully without crashing
- **FR-012**: System MUST handle connection failures to LM Studio gracefully without crashing
- **FR-013**: System MUST track performance metrics: LM Studio response time, Elasticsearch execution time, end-to-end query time
- **FR-014**: System MUST support running batch of 30-50 test queries and generating metrics report
- **FR-015**: System MUST calculate and report DSL validity rate (percentage of queries generating syntactically valid DSL)
- **FR-016**: System MUST calculate and report result accuracy rate (percentage of queries returning correct results based on manual verification)

### Key Entities

- **Natural Language Query**: User input in plain text describing desired search (e.g., "Find all Qatari nationals in Doha")
- **Index Mapping**: Elasticsearch schema definition including field names, types, and properties for person_details, vehicle, or violations index
- **Query DSL**: Elasticsearch Query DSL JSON object generated by LM Studio based on natural language input and index mapping
- **Query Translation Log**: Record of each translation attempt including: timestamp, natural language input, index mapping sent, generated Query DSL, validation result, execution result, performance metrics
- **Test Corpus**: Collection of 30-50 MOI-specific queries covering person lookups, vehicle searches, and violation queries
- **Metrics Report**: Summary statistics showing DSL validity rate, result accuracy rate, average response times, organized by query category (person/vehicle/violation)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Analyst can submit natural language query and receive Elasticsearch results in under 5 seconds for 90% of simple queries
- **SC-002**: System successfully generates syntactically valid Query DSL for at least 70% of test corpus queries
- **SC-003**: System returns correct results (verified manually) for at least 70% of test corpus queries
- **SC-004**: System processes complete test corpus of 30-50 queries and produces metrics report without crashing
- **SC-005**: All query translations are logged with sufficient detail to enable debugging and prompt engineering improvements
- **SC-006**: System gracefully handles connection failures without data loss or requiring restart
- **SC-007**: Baseline metrics (DSL validity rate and result accuracy rate) are documented and saved for Phase 2 comparison

### Assumptions

- Elasticsearch 8.11 container is running and accessible at localhost:9200
- LM Studio is running with EQuIP_3B model loaded and API available at localhost:1234
- Existing indices (person_details, vehicle, violations) contain test data for validation
- Test corpus of 30-50 queries will be manually created covering representative MOI use cases
- Result accuracy will be determined through manual verification for baseline (automated verification may be added in Phase 2)
- Single-index queries only (multi-index queries are out of scope for Phase 1)
- Query results verification focuses on correctness, not completeness or ranking quality
