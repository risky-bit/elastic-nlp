"""
Ground-truth query accuracy test suite.

Replaces evaluate_v3.py with a proper pytest suite. Every test corresponds
to one query in data/test_corpus_v2.json. Pass means the model generated a
DSL that returned the exact same document count as the hand-verified correct
query against the live Elasticsearch cluster.

Markers:
    accuracy        — requires live ES + LLM (all tests here)
    single_index    — queries against one index only
    multi_index     — two-step join queries
    slow            — any test; inference is ~3-6s per query

Usage:
    # Full suite (all 126):
    pytest tests/integration/test_query_accuracy.py -m accuracy

    # Single-index only (faster):
    pytest tests/integration/test_query_accuracy.py -m "accuracy and single_index"

    # Multi-index joins only:
    pytest tests/integration/test_query_accuracy.py -m "accuracy and multi_index"

    # One category (e.g. visa-main):
    pytest tests/integration/test_query_accuracy.py -k "VS"

    # One query:
    pytest tests/integration/test_query_accuracy.py -k "VS09"

Requirements:
    - Elasticsearch running and reachable (ES_HOST / ES_PORT in .env)
    - LLM inference server running with v9 adapter:
        venv/bin/mlx_lm.server --model EQuIP-Queries/EQuIP_3B \
            --adapter-path adapters/equip_moi_v9 --port 1234
"""

import json
import pytest
from pathlib import Path

# ── load corpus at module level so @pytest.mark.parametrize has IDs ──────────
# (fixtures aren't available at collection time)

_CORPUS_PATH = Path(__file__).parent.parent.parent / "data" / "test_corpus_v2.json"

if _CORPUS_PATH.exists():
    with open(_CORPUS_PATH) as _f:
        _ALL_ITEMS = {item["id"]: item for item in json.load(_f)}
else:
    _ALL_ITEMS = {}

_SINGLE_IDS = sorted(
    qid for qid, item in _ALL_ITEMS.items() if item["type"] == "single"
)
_MULTI_IDS = sorted(
    qid for qid, item in _ALL_ITEMS.items() if item["type"] == "multi"
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _count_single(es_client, index, dsl_str, transformer):
    """Parse DSL string, transform, run ES COUNT, return int count."""
    try:
        parsed = json.loads(dsl_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Model returned invalid JSON: {e}\nRaw: {dsl_str[:300]}")

    transformed = transformer.transform(parsed)

    try:
        result = es_client._client.count(index=index, body=transformed)
        return result["count"]
    except Exception as e:
        pytest.fail(f"ES COUNT failed: {e}\nDSL: {json.dumps(transformed)[:300]}")


# ── single-index tests ────────────────────────────────────────────────────────

@pytest.mark.accuracy
@pytest.mark.single_index
@pytest.mark.slow
@pytest.mark.parametrize("query_id", _SINGLE_IDS)
def test_single_index_accuracy(query_id, corpus, ground_truth, generator, es_client, transformer):
    """
    Model must generate a DSL that returns the exact expected document count.

    Each parametrized case is one query from the test corpus.
    Failure message shows the query, expected count, actual count, and generated DSL
    so failures are immediately actionable without digging through logs.
    """
    item = corpus[query_id]
    query = item["query"]
    index = item["index"]

    if query_id not in ground_truth:
        pytest.skip(f"{query_id} has no ground truth entry")

    expected_count = ground_truth[query_id]["expected_count"]

    # Generate DSL via model
    result = generator.generate_query(query, index)

    if result["status"] == "validation_failed":
        pytest.fail(
            f"Model returned invalid DSL\n"
            f"Query: {query}\n"
            f"Error: {result.get('error')}\n"
            f"Raw: {result.get('generated_dsl', '')[:300]}"
        )

    if result["status"] == "execution_failed":
        pytest.fail(
            f"ES rejected the generated DSL\n"
            f"Query: {query}\n"
            f"Error: {result.get('error')}\n"
            f"DSL: {result.get('generated_dsl', '')[:300]}"
        )

    dsl_str = result["generated_dsl"]
    actual_count = _count_single(es_client, index, dsl_str, transformer)

    assert actual_count == expected_count, (
        f"\nQuery:    {query}\n"
        f"Expected: {expected_count}\n"
        f"Got:      {actual_count}\n"
        f"DSL:      {dsl_str}"
    )


# ── multi-index tests ─────────────────────────────────────────────────────────

@pytest.mark.accuracy
@pytest.mark.multi_index
@pytest.mark.slow
@pytest.mark.parametrize("query_id", _MULTI_IDS)
def test_multi_index_accuracy(query_id, corpus, ground_truth, planner, executor):
    """
    Model must generate a valid multi-index plan whose final step returns
    the exact expected document count.
    """
    item = corpus[query_id]
    query = item["query"]

    if query_id not in ground_truth:
        pytest.skip(f"{query_id} has no ground truth entry")

    expected_count = ground_truth[query_id]["expected_count"]

    # Generate plan via model
    plan_result = planner.plan(query)

    if plan_result.get("status") != "success":
        pytest.fail(
            f"Planner failed to generate a valid plan\n"
            f"Query: {query}\n"
            f"Error: {plan_result.get('error')}"
        )

    plan = plan_result["plan"]

    # Validate plan structure
    is_valid, err = planner.validate_plan(plan)
    if not is_valid:
        pytest.fail(
            f"Generated plan is structurally invalid\n"
            f"Query: {query}\n"
            f"Error: {err}\n"
            f"Plan:  {json.dumps(plan)[:400]}"
        )

    # Execute plan
    exec_result = executor.execute_plan(plan)
    exec_status = exec_result.get("status")

    if exec_status == "execution_failed":
        pytest.fail(
            f"Plan execution failed\n"
            f"Query: {query}\n"
            f"Error: {exec_result.get('error')}\n"
            f"Plan:  {json.dumps(plan)[:400]}"
        )

    actual_count = exec_result.get("total_count", 0)

    assert actual_count == expected_count, (
        f"\nQuery:    {query}\n"
        f"Expected: {expected_count}\n"
        f"Got:      {actual_count}\n"
        f"Steps:    {json.dumps(exec_result.get('steps_executed'), indent=2)}\n"
        f"Plan:     {json.dumps(plan)}"
    )


# ── category-level pass-rate tests ───────────────────────────────────────────
# These are not parametrized — they run the whole category and assert a minimum
# pass rate. Useful for CI where you want to enforce "visa-main must stay ≥80%"
# without failing the build on any single flaky query.

_CATEGORY_THRESHOLDS = {
    # category_prefix: minimum pass rate (fraction)
    "N":  1.00,   # violations — must stay perfect
    "RL": 1.00,   # relationships — must stay perfect
    "SP": 1.00,   # sponsor — must stay perfect
    "VS": 0.80,   # visa-main — hard-won, don't regress below 80%
    "VA": 0.80,   # visa-app
    "E":  0.80,   # exit/entry
    "V":  0.80,   # vehicle
    "P":  0.75,   # person
    "M":  0.80,   # multi-index
}


@pytest.mark.accuracy
@pytest.mark.slow
@pytest.mark.parametrize("prefix,threshold", _CATEGORY_THRESHOLDS.items())
def test_category_pass_rate(
    prefix, threshold,
    corpus, ground_truth, generator, planner, executor, es_client, transformer
):
    """
    Assert that a full query category stays above its minimum pass rate.
    Catches regressions when a new adapter drops a previously-working category.
    """
    category_ids = [
        qid for qid in _ALL_ITEMS
        if qid.startswith(prefix) and qid in ground_truth
    ]

    if not category_ids:
        pytest.skip(f"No ground-truth queries found for prefix '{prefix}'")

    passed = 0
    failed_details = []

    for qid in sorted(category_ids):
        item = corpus[qid]
        query = item["query"]
        expected = ground_truth[qid]["expected_count"]
        actual = None

        try:
            if item["type"] == "multi":
                plan_result = planner.plan(query)
                if plan_result.get("status") != "success":
                    failed_details.append(f"  {qid}: plan failed — {plan_result.get('error','')[:80]}")
                    continue
                exec_result = executor.execute_plan(plan_result["plan"])
                actual = exec_result.get("total_count", 0)
            else:
                result = generator.generate_query(query, item["index"])
                if result["status"] in ("validation_failed", "execution_failed"):
                    failed_details.append(f"  {qid}: {result['status']} — {result.get('error','')[:80]}")
                    continue
                actual = _count_single(es_client, item["index"], result["generated_dsl"], transformer)
        except Exception as e:
            failed_details.append(f"  {qid}: exception — {str(e)[:80]}")
            continue

        if actual == expected:
            passed += 1
        else:
            failed_details.append(f"  {qid}: expected={expected} got={actual} — {query[:60]}")

    total = len(category_ids)
    rate = passed / total

    assert rate >= threshold, (
        f"\nCategory '{prefix}': {passed}/{total} = {rate:.0%} — below threshold {threshold:.0%}\n"
        f"Failures:\n" + "\n".join(failed_details)
    )
