#!/usr/bin/env python3
"""
evaluate_v3.py — Ground-truth-based evaluation.

For every query in the corpus:
  1. Generate DSL via LLM (same as v2)
  2. Apply DSLTransformer (nationality names → codes)
  3. Run COUNT query against ES (not search — avoids 10k cap)
  4. Compare actual_count to expected_count from data/ground_truth.json

Statuses:
  correct          — actual_count == expected_count
  wrong_count      — valid DSL, executed, but returned wrong count
  validation_failed — model returned non-JSON or missing 'query' key
  execution_failed  — ES rejected the DSL (400 error)
  no_ground_truth  — query not in ground_truth.json (falls back to v2 logic)

Usage:
    USE_DIRECT_PROMPT=true python evaluate_v3.py [--corpus data/test_corpus_v2.json]
"""

import json
import sys
import time
import argparse
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import Config
from src.es_client import ESClient
from src.llm_client import VLLMClient
from src.query_generator import QueryGenerator
from src.query_planner import MultiIndexQueryPlanner
from src.query_executor import MultiIndexExecutor
from src.dsl_transformer import DSLTransformer
from src.logger import setup_query_translation_logger


def get_actual_count(es, index, dsl_str, transformer):
    """
    Parse generated DSL, apply transformer, run COUNT query.
    Returns (count, error_message).
    """
    try:
        parsed = json.loads(dsl_str)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    try:
        transformed = transformer.transform(parsed)
    except Exception as e:
        return None, f"Transformer error: {e}"

    try:
        result = es._client.count(index=index, body=transformed)
        return result["count"], None
    except Exception as e:
        return None, f"ES count error: {e}"


def evaluate(corpus_path: str):
    config = Config()
    logger = setup_query_translation_logger()

    es_client = ESClient(config)
    es_client.connect()

    llm_client = VLLMClient(config)
    transformer = DSLTransformer(logger)

    generator = QueryGenerator(es_client, llm_client, config, logger)
    planner = MultiIndexQueryPlanner(llm_client, config, logger)
    executor = MultiIndexExecutor(es_client, logger)

    # Load ground truth
    gt_path = REPO_ROOT / "data" / "ground_truth.json"
    if not gt_path.exists():
        print(f"ERROR: {gt_path} not found. Run scripts/build_ground_truth.py first.")
        sys.exit(1)
    with open(gt_path) as f:
        ground_truth = json.load(f)

    with open(corpus_path) as f:
        corpus = json.load(f)

    results = []
    counters = {
        'total': 0,
        'correct': 0,
        'wrong_count': 0,
        'validation_failed': 0,
        'execution_failed': 0,
        'no_ground_truth': 0,
    }

    tier_counters = {}
    index_counters = {}

    print(f"\nEvaluating {len(corpus)} queries from {corpus_path}")
    print(f"Model: {config.VLLM_MODEL}")
    print(f"Ground truth: {len(ground_truth)} entries")
    print("=" * 90)

    for i, item in enumerate(corpus, 1):
        qid = item['id']
        query = item['query']
        qtype = item['type']
        tier = item['tier']
        index = item.get('index', '')

        gt = ground_truth.get(qid)
        expected_count = gt['expected_count'] if gt else None

        print(f"[{i:3d}/{len(corpus)}] {qid} ({tier}) — {query[:60]}")

        start = time.time()
        status = 'no_ground_truth'
        error = ''
        actual_count = 0
        generated_dsl = None

        try:
            if qtype == 'multi':
                plan_result = planner.plan(query)
                if plan_result.get('status') != 'success':
                    status = 'validation_failed'
                    error = plan_result.get('error', 'Plan generation failed')
                else:
                    plan = plan_result['plan']
                    exec_result = executor.execute_plan(plan)
                    exec_status = exec_result.get('status', 'other')
                    actual_count = exec_result.get('total_count', 0)
                    error = exec_result.get('error', '')
                    generated_dsl = json.dumps(plan)

                    if exec_status == 'execution_failed':
                        status = 'execution_failed'
                    elif gt is not None:
                        status = 'correct' if actual_count == expected_count else 'wrong_count'
                    else:
                        status = 'no_ground_truth'

            else:
                # Single-index: generate DSL via LLM
                result = generator.generate_query(query, index)
                gen_status = result.get('status', 'other')
                generated_dsl = result.get('generated_dsl')
                error = result.get('error', '')

                if gen_status == 'validation_failed':
                    status = 'validation_failed'
                elif gen_status == 'execution_failed':
                    status = 'execution_failed'
                elif generated_dsl and gt is not None:
                    # Run COUNT to get exact actual count (bypasses 10k hits cap)
                    cnt, cnt_err = get_actual_count(es_client, index, generated_dsl, transformer)
                    if cnt_err:
                        status = 'execution_failed'
                        error = cnt_err
                        actual_count = 0
                    else:
                        actual_count = cnt
                        status = 'correct' if actual_count == expected_count else 'wrong_count'
                else:
                    actual_count = result.get('result_count', 0)
                    status = 'no_ground_truth'

        except Exception as e:
            status = 'validation_failed'
            error = str(e)

        latency_ms = (time.time() - start) * 1000

        # Display
        if status == 'correct':
            icon = '✓'
            detail = f"count={actual_count} == expected={expected_count}"
        elif status == 'wrong_count':
            icon = '✗'
            detail = f"count={actual_count} ≠ expected={expected_count}"
        elif status == 'no_ground_truth':
            icon = '?'
            detail = f"count={actual_count} (no ground truth)"
        else:
            icon = '✗'
            detail = f"{error[:60]}"

        print(f"         {icon} {status:20s} | {detail} | {latency_ms:.0f}ms")

        # Tally
        counters['total'] += 1
        if status in counters:
            counters[status] += 1

        tier_key = tier
        if tier_key not in tier_counters:
            tier_counters[tier_key] = {'total': 0, 'correct': 0}
        tier_counters[tier_key]['total'] += 1
        if status == 'correct':
            tier_counters[tier_key]['correct'] += 1

        idx_key = index if qtype != 'multi' else 'multi_index'
        if idx_key not in index_counters:
            index_counters[idx_key] = {'total': 0, 'correct': 0}
        index_counters[idx_key]['total'] += 1
        if status == 'correct':
            index_counters[idx_key]['correct'] += 1

        results.append({
            'id': qid,
            'query': query,
            'type': qtype,
            'tier': tier,
            'index': index,
            'status': status,
            'actual_count': actual_count,
            'expected_count': expected_count,
            'latency_ms': round(latency_ms, 1),
            'error': error,
            'generated_dsl': generated_dsl,
        })

    # Summary
    total = counters['total']
    correct = counters['correct']
    wrong = counters['wrong_count']
    val_fail = counters['validation_failed']
    exec_fail = counters['execution_failed']
    no_gt = counters['no_ground_truth']
    with_gt = total - no_gt

    print("\n" + "=" * 90)
    print("RESULTS SUMMARY (ground-truth count comparison)")
    print("=" * 90)
    print(f"Total queries:         {total}")
    print(f"With ground truth:     {with_gt}")
    print(f"Correct count:         {correct}/{with_gt}  ({correct/with_gt*100:.1f}% of evaluated)")
    print(f"Wrong count:           {wrong}/{with_gt}")
    print(f"Validation failed:     {val_fail}/{total}")
    print(f"Execution failed:      {exec_fail}/{total}")
    print(f"No ground truth:       {no_gt}/{total}")

    print("\nBy tier:")
    for tier in ['simple', 'medium', 'hard']:
        if tier in tier_counters:
            t = tier_counters[tier]
            evaluated = t['total']
            pct = t['correct'] / evaluated * 100 if evaluated else 0
            print(f"  {tier:8s}: {t['correct']}/{evaluated} ({pct:.1f}%)")

    print("\nBy index:")
    for idx, counts in sorted(index_counters.items()):
        evaluated = counts['total']
        pct = counts['correct'] / evaluated * 100 if evaluated else 0
        short = idx.replace('moi-', '').replace('-details-v1', '').replace('-v1', '')
        print(f"  {short:40s}: {counts['correct']}/{evaluated} ({pct:.1f}%)")

    # Wrong count details
    wrong_results = [r for r in results if r['status'] == 'wrong_count']
    if wrong_results:
        print(f"\nWrong count ({len(wrong_results)}):")
        for r in wrong_results:
            print(f"  [{r['id']}] got={r['actual_count']} expected={r['expected_count']} — {r['query'][:60]}")
            if r['generated_dsl']:
                print(f"         DSL: {r['generated_dsl'][:100]}")

    failures = [r for r in results if r['status'] in ('validation_failed', 'execution_failed')]
    if failures:
        print(f"\nFailed DSL ({len(failures)}):")
        for r in failures:
            print(f"  [{r['id']}] {r['status']} — {r['query'][:60]}")
            if r['error']:
                print(f"         {r['error'][:80]}")

    # Save
    out_path = "data/eval_results_v3.json"
    with open(out_path, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'with_ground_truth': with_gt,
                'correct': correct,
                'wrong_count': wrong,
                'validation_failed': val_fail,
                'execution_failed': exec_fail,
                'correct_rate': round(correct / with_gt * 100, 1) if with_gt else 0,
            },
            'by_tier': tier_counters,
            'by_index': index_counters,
            'results': results,
        }, f, indent=2)

    print(f"\nDetailed results saved to: {out_path}")
    return correct / with_gt * 100 if with_gt else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', default='data/test_corpus_v2.json')
    args = parser.parse_args()

    accuracy = evaluate(args.corpus)
    print(f"\nFinal accuracy (ground-truth count match): {accuracy:.1f}%")
