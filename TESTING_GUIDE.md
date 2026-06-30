# Phase 4 MVP - Testing Guide

## Current Status

✅ **Elasticsearch**: Running with real test data (50 person_details, 50 violations)
✅ **Configuration**: .env configured correctly
✅ **Code**: Phase 4 implementation complete (all tests passing)
⏳ **vLLM**: Downloading (in progress)

## Monitor vLLM Download Progress

### Check if vLLM container is running
```bash
docker-compose ps
```

### Watch vLLM logs (real-time)
```bash
docker-compose logs -f vllm
```

### Check vLLM API health
```bash
curl http://localhost:8000/v1/models
```

**Expected response when ready:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "EQuIP-Queries/EQuIP_3B",
      "object": "model",
      ...
    }
  ]
}
```

## Once vLLM is Ready

### Option 1: Run Quick Test Script (Recommended)
```bash
python test_real_query.py
```

This will:
- Test 3 different queries on your real person_details data
- Show generated Query DSL
- Display results and latency metrics
- Log everything to `logs/query_translations.jsonl`

### Option 2: Interactive Mode
```bash
python -m src.cli query --interactive --index person_details --verbose
```

Try these queries:
- "Find all Qatari nationals"
- "Show me people named Peter"
- "Find female residents"
- "Show people born in Al-Khor"
- "Find suspended residents"

### Option 3: Single Query
```bash
python -m src.cli query "Find all Qatari nationals" --index person_details --verbose
```

## What to Look For

### 1. DSL Generation Quality
- Does the LLM use correct field names? (`CL_FIRST_ENGLISH_NAME`, `PRESENT_NATIONALITY`, etc.)
- Is the generated JSON valid?
- Does it use appropriate query types (match, term, range, bool)?

### 2. Result Accuracy
- Do results match the query intent?
- Are the returned documents relevant?

### 3. Performance
- LLM latency (how long to generate DSL)
- ES latency (how long to execute query)
- Total end-to-end latency

## Example Expected Output

```
Processing query: Find all Qatari nationals
Target index: person_details
✓ Query executed successfully

Generated DSL:
{
  "query": {
    "match": {
      "PRESENT_NATIONALITY": "QAT"
    }
  }
}

Results: 12 document(s) found

Top results:
1. {
  "APPLICANT_QID": "95588098696",
  "CL_FIRST_ENGLISH_NAME": "Peter",
  "PRESENT_NATIONALITY": "QAT",
  ...
}
```

## Troubleshooting

### vLLM takes too long to download
- The Docker image is ~4-5 GB
- The model download is ~3-7 GB
- Total download time: 5-30 minutes (depending on internet speed)

### vLLM fails to start
```bash
# Check logs for errors
docker-compose logs vllm

# Try CPU-only version (slower but more compatible)
docker-compose -f docker-compose.cpu.yml up -d vllm
```

### Connection errors
```bash
# Verify Elasticsearch is accessible
curl -u elastic:elastic http://localhost:9200/_cluster/health

# Verify vLLM is accessible
curl http://localhost:8000/v1/models
```

## Next Steps After Testing

1. **Analyze baseline metrics** from `logs/query_translations.jsonl`
2. **Calculate DSL validity rate** (% of valid JSON)
3. **Calculate result accuracy rate** (% of successful executions)
4. **Identify failure patterns** (what queries fail and why)
5. **Decide**: Continue to Phases 5-8 OR improve Phase 4 based on results
