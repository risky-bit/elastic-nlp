# Phase 2: Multi-Index Query Planning

**Branch**: `002-phase2-multi-index`
**Depends on**: Phase 1 complete (LoRA v4, 100% single-index accuracy)

## Goal

Extend the system to handle queries that span multiple indices using application-level joins.
Example: "Find speeding violations for Qatari nationals" requires:
1. Query person index → get QIDs of Qatari nationals
2. Use those QIDs to filter violations index → get their speeding violations

ES has no native cross-index join. We implement it in Python.

## Join Fields (CRITICAL)

- `prs_qid` (person) ↔ `VLN_OWNQID` (violations)
- `prs_qid` (person) ↔ `VRG_OWNQID` (vehicle) — note: verify field exists in vehicle index

## Query Plan Format

The LLM outputs a `multi_index` plan instead of a single DSL:

```json
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
```

`$step_1` is a placeholder replaced at runtime with the extracted field values from step 1.

## User Stories

### US5: Person → Violations join
"Find speeding violations for Qatari nationals"
"Show unpaid violations for Pakistani drivers"
"Find violations on Corniche Road for Indian nationals"

### US6: Person → Vehicle join
"Find vehicles owned by Qatari males"
"Show Toyota vehicles registered to Pakistani nationals"
"Find expired vehicles owned by Egyptians"

### US7: Three-way (stretch goal)
"Find speeding violations for vehicles owned by Qataris"
person → vehicle (get plate numbers) → violations (filter by plate)

---

## Phase 1: Foundation (T001–T010)

- [ ] T001 Verify VRG_OWNQID field exists in vehicle index — `es.get_mapping('moi-vehicle-info-v1')` and check
- [ ] T002 Create `src/query_planner.py` — MultiIndexQueryPlanner class:
  - `is_multi_index(nl_query) -> bool` — detect if query needs a join
  - `plan(nl_query) -> dict` — call LLM, return parsed query plan
  - `validate_plan(plan) -> (bool, error)` — validate plan structure
- [ ] T003 Create `src/query_executor.py` — MultiIndexExecutor class:
  - `execute_plan(plan) -> dict` — run steps sequentially, inject IDs between steps
  - `_extract_ids(results, field) -> list` — pull field values from ES hits
  - `_inject_ids(query, step_ref, ids) -> dict` — replace `$step_N` with actual `terms` values
- [ ] T004 Write unit tests for MultiIndexQueryPlanner (tests/unit/test_query_planner.py)
- [ ] T005 Write unit tests for MultiIndexExecutor (tests/unit/test_query_executor.py)
- [ ] T006 Update `src/query_generator.py` to route single vs multi-index queries
- [ ] T007 Update `src/cli.py` — add routing for multi-index result display

## Phase 2: Training Data (T011–T015)

- [ ] T011 Ingest person QID data — ensure person records have prs_qid values that match VLN_OWNQID in violations
- [ ] T012 Create `data/generate_multi_index_training.py` — generate (NL → query plan) pairs:
  - Person→Violations: nationality+violation_type, nationality+violation_status, gender+location, etc.
  - Person→Vehicle: nationality+make, nationality+color, gender+status, etc.
  - Target: 200+ validated pairs
- [ ] T013 Validate multi-index training pairs — execute each plan step-by-step against ES
- [ ] T014 Combine with Phase 1 training data — single-index pairs remain, add multi-index on top
- [ ] T015 Run LoRA fine-tuning on combined dataset — adapters/equip_moi_v5

## Phase 3: Multi-Index Test Corpus (T016–T020)

- [ ] T016 Create `data/test_corpus_multi.json` — 24 multi-index queries (12 person→violations, 12 person→vehicle)
- [ ] T017 Run corpus evaluation
- [ ] T018 Generate metrics report
- [ ] T019 Compare against Phase 1 baseline
- [ ] T020 Document failures and iterate if needed

---

## Success Criteria

- Multi-index query plan validity rate: ≥70%
- End-to-end result accuracy: ≥70%
- Single-index accuracy must not regress (stay at 100%)
