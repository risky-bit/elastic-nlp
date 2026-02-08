# Quickstart Guide: Phase 1 Baseline NL-to-Elasticsearch Query System

**Date**: 2026-02-03
**Feature**: Phase 1 Baseline - NL to Elasticsearch Query System
**Branch**: 001-phase1-baseline

## Overview

This guide walks you through setting up and running the Phase 1 baseline system for natural language to Elasticsearch query translation using EQuIP_3B model via LM Studio.

---

## Prerequisites

Before starting, ensure you have:

1. **Python 3.10+** installed
   ```bash
   python --version  # Should show 3.10 or higher
   ```

2. **Docker** installed and running (for Elasticsearch)
   ```bash
   docker --version
   ```

3. **Elasticsearch 8.11** container running
   ```bash
   docker ps | grep elasticsearch  # Should show running container
   ```

4. **LM Studio** installed and running with EQuIP_3B model
   - Download from: https://lmstudio.ai/
   - Load EQuIP_3B model
   - Start local server on port 1234

5. **Git** repository cloned
   ```bash
   git clone <repository-url>
   cd moi-elastic-nlp
   git checkout 001-phase1-baseline
   ```

---

## Step 1: Environment Setup

### 1.1 Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Verify activation
which python  # Should point to venv/bin/python
```

### 1.2 Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "elasticsearch|requests|pytest"
```

### 1.3 Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Required `.env` configuration**:
```bash
# Elasticsearch Configuration
ES_HOST=localhost
ES_PORT=9200
ES_USER=elastic
ES_PASSWORD=elastic  # Use your actual password

# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=EQuIP_3B

# LLM Parameters
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=500

# Elasticsearch Indices
ES_INDEX_PERSON=person_details
ES_INDEX_VEHICLE=vehicle
ES_INDEX_VIOLATIONS=violations
```

---

## Step 2: Verify Infrastructure

### 2.1 Check Elasticsearch Connection

```bash
# Verify ES is running and accessible
curl -u elastic:elastic "http://localhost:9200/_cluster/health?pretty"

# Expected output: status "green" or "yellow"
```

### 2.2 Check Available Indices

```bash
# List available indices
curl -u elastic:elastic "http://localhost:9200/_cat/indices?v" | grep -E "person_details|vehicle|violations"

# Expected: See person_details, vehicle, violations indices with document counts
```

### 2.3 Verify LM Studio API

```bash
# Test LM Studio API endpoint
curl -X POST http://localhost:1234/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "EQuIP_3B",
    "prompt": "Test prompt",
    "max_tokens": 10
  }'

# Expected: JSON response with "choices" array
```

---

## Step 3: Run Initial Tests

### 3.1 Run Unit Tests

```bash
# Run unit tests (no external dependencies)
pytest tests/unit/ -v

# Expected: All tests should pass (or be skipped if not implemented yet)
```

### 3.2 Run Integration Tests

```bash
# Run integration tests (requires ES + LM Studio)
pytest tests/integration/ -v --timeout=30

# Expected: Tests connect to ES and LM Studio, run end-to-end queries
```

### 3.3 Run Full Test Suite

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Expected: Coverage report showing tested modules
```

---

## Step 4: Run Single Query (Manual Testing)

### 4.1 Interactive Query Execution

```bash
# Run CLI in interactive mode
python -m src.cli query --interactive

# Example session:
# > Enter natural language query: Find person named Ahmed Al-Mansoori
# > Target index (person_details/vehicle/violations): person_details
#
# Generated Query DSL:
# {
#   "query": {
#     "match": {
#       "name": "Ahmed Al-Mansoori"
#     }
#   }
# }
#
# Results: 2 documents found
# [Result details displayed...]
```

### 4.2 Single Query via Command

```bash
# Run single query directly
python -m src.cli query \
  --query "Find all Qatari nationals" \
  --index person_details

# Expected: Query DSL generated, executed, results displayed
```

---

## Step 5: Run Test Corpus

### 5.1 Prepare Test Corpus

```bash
# Test corpus should be in data/test_corpus.json
# Verify it exists:
ls -lh data/test_corpus.json

# View first few queries:
head -20 data/test_corpus.json
```

### 5.2 Execute Full Test Corpus

```bash
# Run all queries in test corpus
python -m src.cli batch \
  --corpus data/test_corpus.json \
  --output logs/batch_results.json

# Expected: Processes 30-50 queries, logs to logs/query_translations.jsonl
```

### 5.3 View Execution Logs

```bash
# Check query translation logs
tail -5 logs/query_translations.jsonl | jq .

# View summary
wc -l logs/query_translations.jsonl  # Should match corpus size
```

---

## Step 6: Generate Metrics Report

### 6.1 Calculate Baseline Metrics

```bash
# Generate metrics report from logs
python -m src.cli metrics \
  --input logs/query_translations.jsonl \
  --output reports/phase1_baseline_metrics.json

# Expected: Generates metrics report with DSL validity rate, accuracy rate
```

### 6.2 View Metrics Report

```bash
# View metrics report
cat reports/phase1_baseline_metrics.json | jq .

# Expected output format:
# {
#   "report_id": "...",
#   "generated_at": "...",
#   "corpus_size": 50,
#   "dsl_validity_rate": 0.74,
#   "result_accuracy_rate": 0.72,
#   "avg_llm_latency_ms": 1450.5,
#   "avg_es_latency_ms": 52.3,
#   "queries_by_category": {...}
# }
```

### 6.3 Compare Against Success Criteria

**Success Criteria (from spec.md)**:
- DSL validity rate: ≥70% ✓ (74% achieved in example)
- Result accuracy rate: ≥70% ✓ (72% achieved in example)
- End-to-end latency: <5s for 90% of queries
- No crashes processing full corpus

```bash
# Check if thresholds met
python -m src.cli metrics-check \
  --report reports/phase1_baseline_metrics.json \
  --threshold-validity 0.70 \
  --threshold-accuracy 0.70

# Expected: "✓ Phase 1 baseline thresholds met" or specific failures
```

---

## Step 7: Troubleshooting

### 7.1 Elasticsearch Connection Issues

**Problem**: `ConnectionError: Connection to localhost:9200 failed`

**Solution**:
```bash
# Check if ES container is running
docker ps | grep elasticsearch

# If not running, start it:
docker start elasticsearch

# Wait for ES to be ready
sleep 10
curl -u elastic:elastic "http://localhost:9200/_cluster/health"
```

### 7.2 LM Studio API Issues

**Problem**: `ConnectionError: Connection to localhost:1234 failed`

**Solution**:
1. Open LM Studio application
2. Go to "Local Server" tab
3. Ensure server is started and shows "Running on port 1234"
4. Verify EQuIP_3B model is loaded

### 7.3 Invalid Query DSL Generated

**Problem**: Many queries generating invalid JSON or invalid DSL

**Possible causes**:
- LLM temperature too high (increase determinism)
- Prompt template not clear enough
- Index mapping not provided correctly

**Debug steps**:
```bash
# Check a failing query in detail
python -m src.cli query \
  --query "Your failing query here" \
  --index person_details \
  --debug

# This will show:
# - Full prompt sent to LLM
# - Raw LLM response
# - Validation errors
# - ES error messages
```

### 7.4 Missing Test Corpus

**Problem**: `FileNotFoundError: data/test_corpus.json not found`

**Solution**:
```bash
# Test corpus needs to be created manually for Phase 1
# Use the template:
cat > data/test_corpus.json << 'EOF'
[
  {
    "query_id": "TC001",
    "query_text": "Find person named Ahmed Al-Mansoori",
    "target_index": "person_details",
    "query_category": "person_lookup",
    "notes": "Basic match query"
  },
  {
    "query_id": "TC002",
    "query_text": "Show all Qatari nationals",
    "target_index": "person_details",
    "query_category": "person_lookup",
    "notes": "Keyword match on nationality field"
  }
]
EOF

# Then add 28-48 more queries following the same format
```

---

## Step 8: Development Workflow (TDD)

### 8.1 Adding New Functionality

When adding new features, follow strict TDD:

```bash
# 1. Write test first (RED)
nano tests/unit/test_new_feature.py
pytest tests/unit/test_new_feature.py  # Should FAIL

# 2. Implement minimum code (GREEN)
nano src/new_module.py
pytest tests/unit/test_new_feature.py  # Should PASS

# 3. Refactor if needed
nano src/new_module.py
pytest tests/unit/test_new_feature.py  # Should still PASS

# 4. Run full test suite
pytest tests/ -v
```

### 8.2 Testing Changes

```bash
# Before committing, always run:
pytest tests/ -v --cov=src  # All tests + coverage
python -m src.cli query --query "Test query" --index person_details  # Smoke test
```

---

## Step 9: Next Steps

After completing Phase 1 baseline:

1. **Analyze Results**: Review metrics report, identify failure patterns
2. **Document Findings**: Update research.md with observed model behavior
3. **Prepare for Phase 2**: Baseline metrics become comparison point
4. **Create Pull Request**: Document baseline results in PR description

---

## Quick Reference

### Essential Commands

```bash
# Activate environment
source venv/bin/activate

# Run single query
python -m src.cli query --query "Your query" --index person_details

# Run test corpus
python -m src.cli batch --corpus data/test_corpus.json

# Generate metrics
python -m src.cli metrics --input logs/query_translations.jsonl

# Run tests
pytest tests/ -v

# Check ES health
curl -u elastic:elastic "http://localhost:9200/_cluster/health"
```

### Important File Locations

- **Configuration**: `.env` (never commit!)
- **Test Corpus**: `data/test_corpus.json`
- **Query Logs**: `logs/query_translations.jsonl`
- **Metrics Reports**: `reports/phase1_baseline_metrics.json`
- **Prompt Templates**: `data/prompts/prompt_template_v1.txt`
- **Index Mappings**: `data/mappings/*.json`

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ES_HOST` | Yes | localhost | Elasticsearch host |
| `ES_PORT` | Yes | 9200 | Elasticsearch port |
| `ES_USER` | Yes | - | ES username |
| `ES_PASSWORD` | Yes | - | ES password |
| `LM_STUDIO_URL` | Yes | http://localhost:1234/v1 | LM Studio API endpoint |
| `LM_STUDIO_MODEL` | Yes | EQuIP_3B | Model name |
| `LLM_TEMPERATURE` | No | 0.1 | Sampling temperature |
| `LLM_MAX_TOKENS` | No | 500 | Max response tokens |

---

## Support

For issues during development:

1. Check logs in `logs/` directory
2. Run with `--debug` flag for detailed output
3. Review constitution compliance in `specs/001-phase1-baseline/plan.md`
4. Consult data model in `specs/001-phase1-baseline/data-model.md`

---

## Constitution Compliance

This quickstart follows all constitution principles:

✅ **Modular Architecture**: Clear module boundaries (es_client, llm_client, query_generator)
✅ **Test-First Development**: TDD workflow documented (Step 8)
✅ **Dependency Versioning**: requirements.txt pins versions, .env.example documents config
✅ **Reproducibility**: All query translations logged with full context
✅ **Integration Testing**: pytest runs against real Docker ES container

**Phase 1 Goal**: Establish baseline metrics (70% DSL validity, 70% result accuracy) for Phase 2 comparison.
