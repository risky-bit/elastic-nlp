# MOI Elasticsearch NLP Query System

**Phase 1 Baseline**: Natural Language to Elasticsearch Query DSL Translation using EQuIP_3B

## Project Overview

This project evaluates different approaches to natural language query translation for Elasticsearch, specifically tailored for MOI (Ministry of Interior) use cases involving person lookups, vehicle records, and traffic violations.

### Phase 1 Goals

- **Baseline Establishment**: Connect EQuIP_3B model (via vLLM) to Elasticsearch 8.11
- **Test Corpus**: Evaluate system on 30-50 MOI-specific queries
- **Success Metrics**:
  - DSL Validity Rate ≥70%
  - Result Accuracy Rate ≥70%
- **Purpose**: Establish baseline metrics for Phase 2 comparison

### Architecture

```
Natural Language Query
  ↓
EQuIP_3B (via vLLM API)
  ↓
Elasticsearch Query DSL
  ↓
Elasticsearch 8.11
  ↓
Results
```

**Modular Components**:
- `src/config.py`: Environment configuration management
- `src/logger.py`: Structured JSON logging
- `src/es_client.py`: Elasticsearch operations
- `src/llm_client.py`: vLLM API client
- `src/query_generator.py`: Query translation orchestration
- `src/metrics.py`: Performance tracking and reporting
- `src/cli.py`: Command-line interface

## Prerequisites

### Option 1: Docker Compose (Recommended - Easiest)

- **Docker** with Docker Compose installed
- **NVIDIA Docker** (for GPU support, optional but recommended)
- **8GB+ RAM** (4GB for Elasticsearch, 4GB+ for vLLM)
- **GPU** (optional, but 10-100x faster inference)

### Option 2: Manual Setup

1. **Python 3.10+** installed
2. **Docker** running with Elasticsearch 8.11
3. **vLLM** server running with EQuIP_3B model
4. **Existing MOI data** in Elasticsearch indices:
   - `person_details`
   - `vehicle`
   - `violations`

## Quick Start

### Setup Option 1: Docker Compose (Recommended)

**Step 1: Start Infrastructure**

```bash
# With GPU (recommended - 10-100x faster)
docker-compose up -d

# OR without GPU (CPU only, slower)
docker-compose -f docker-compose.cpu.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f vllm        # vLLM server logs
docker-compose logs -f elasticsearch  # Elasticsearch logs
```

**Step 2: Wait for Services to Start**

```bash
# Check Elasticsearch health (should show status: green or yellow)
curl -u elastic:elastic "http://localhost:9200/_cluster/health?pretty"

# Check vLLM server (should return model info)
curl http://localhost:8000/v1/models
```

**Step 3: Setup Python Environment**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env - set ES_PASSWORD=elastic (or your custom password)
```

**Step 4: Load MOI Test Data (if needed)**

```bash
# TODO: Add your MOI data loading script here
# Example: python scripts/load_moi_data.py
```

**Step 5: Run a Test Query**

```bash
python -m src.cli query \
  --query "Find person named Ahmed Al-Mansoori" \
  --index person_details
```

**Stopping Services**

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (WARNING: deletes all data!)
docker-compose down -v
```

---

### Setup Option 2: Manual Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Elasticsearch credentials
```

### 2. Start vLLM Server (Manual Setup Only)

```bash
# Install vLLM
pip install vllm

# Start vLLM server with EQuIP_3B model
vllm serve "EQuIP-Queries/EQuIP_3B"

# Server will start on http://localhost:8000
# First run will download the model (~6GB)
```

### 3. Verify Infrastructure

```bash
# Check Elasticsearch
curl -u elastic:your_password "http://localhost:9200/_cluster/health?pretty"

# Check vLLM API
curl http://localhost:8000/v1/models
```

### 3. Run a Single Query

```bash
# Interactive mode
python -m src.cli query --interactive

# Direct query
python -m src.cli query \
  --query "Find person named Ahmed Al-Mansoori" \
  --index person_details
```

### 4. Run Test Corpus

```bash
# Process full test corpus
python -m src.cli batch \
  --corpus data/test_corpus.json \
  --output logs/batch_results.json

# Generate metrics report
python -m src.cli metrics \
  --input logs/query_translations.jsonl \
  --output reports/phase1_baseline_metrics.json
```

## Development

### Test-Driven Development (TDD)

This project follows strict TDD principles per the constitution:

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests (requires ES + LM Studio running)
pytest tests/integration/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Project Structure

```
moi-elastic-nlp/
├── src/                   # Application source code
├── tests/                 # Test suite (unit, integration, contract)
├── data/                  # Test data and reference files
│   ├── mappings/          # Versioned ES index mappings
│   ├── prompts/           # Versioned prompt templates
│   └── test_corpus.json   # 30-50 MOI test queries
├── logs/                  # Generated logs (gitignored)
└── reports/               # Metrics reports (gitignored)
```

## Constitution Compliance

This project adheres to the MOI Elasticsearch NLP Constitution (v1.2.0):

✅ **Modular Architecture**: Clear module boundaries
✅ **Test-First Development**: TDD enforced (NON-NEGOTIABLE)
✅ **Dependency Versioning**: Pinned requirements, versioned prompts/mappings
✅ **Reproducibility**: Structured logging, LLM parameter tracking
✅ **Integration Testing**: pytest-docker for containerized ES

## Phase Roadmap

- **Phase 1 (Current)**: Baseline with EQuIP_3B via LM Studio ← **You are here**
- **Phase 2A**: Custom wrapper with pre/post-processing
- **Phase 2B**: Elastic Cloud 9.2 with Agent Builder MCP
- **Phase 3**: LoRA fine-tuning (conditional, if <80% accuracy in Phase 2)

## Documentation

- [Feature Specification](specs/001-phase1-baseline/spec.md)
- [Implementation Plan](specs/001-phase1-baseline/plan.md)
- [Quickstart Guide](specs/001-phase1-baseline/quickstart.md)
- [Data Model](specs/001-phase1-baseline/data-model.md)
- [Task Breakdown](specs/001-phase1-baseline/tasks.md)

## License

MOI Internal Project
