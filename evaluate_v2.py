#!/usr/bin/env python3
"""
Evaluate LoRA adapter against the full v2 test corpus (126 queries).

Handles both single-index (via QueryGenerator) and multi-index (via QueryPlanner + MultiIndexExecutor).

Usage:
    USE_DIRECT_PROMPT=true python evaluate_v2.py [--adapter equip_moi_v6] [--corpus data/test_corpus_v2.json]
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
from src.logger import setup_query_translation_logger


def evaluate(corpus_path: str):
    config = Config()
    logger = setup_query_translation_logger()

    es_client = ESClient(config)
    es_client.connect()

    llm_client = VLLMClient(config)

    generator = QueryGenerator(es_client, llm_client, config, logger)
    planner = MultiIndexQueryPlanner(llm_client, config, logger)
    executor = MultiIndexExecutor(es_client, logger)

    with open(corpus_path) as f:
        corpus = json.load(f)

    results = []
    counters = {
        'total': 0,
        'success': 0,
        'no_results': 0,
        'validation_failed': 0,
        'execution_failed': 0,
        'other': 0,
    }

    tier_counters = {}
    index_counters = {}

    print(f"\nEvaluating {len(corpus)} queries from {corpus_path}")
    print(f"Model: {config.VLLM_MODEL}")
    print(f"USE_DIRECT_PROMPT: {config.USE_DIRECT_PROMPT}")
    print("=" * 80)

    for i, item in enumerate(corpus, 1):
        qid = item['id']
        query = item['query']
        qtype = item['type']
        tier = item['tier']
        index = item.get('index', '')

        print(f"[{i:3d}/{len(corpus)}] {qid} ({tier}) — {query[:60]}")

        start = time.time()
        status = 'other'
        error = ''
        result_count = 0
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
                    status = exec_result.get('status', 'other')
                    result_count = exec_result.get('total_count', 0)
                    error = exec_result.get('error', '')
                    generated_dsl = json.dumps(plan)
            else:
                result = generator.generate_query(query, index)
                status = result.get('status', 'other')
                result_count = result.get('result_count', 0)
                error = result.get('error', '')
                generated_dsl = result.get('generated_dsl')

        except Exception as e:
            status = 'other'
            error = str(e)

        latency_ms = (time.time() - start) * 1000

        icon = '✓' if status == 'success' else ('○' if status == 'no_results' else '✗')
        print(f"         {icon} {status} | {result_count} docs | {latency_ms:.0f}ms")
        if status not in ('success', 'no_results') and error:
            print(f"           ! {error[:100]}")

        # Tally
        counters['total'] += 1
        if status in counters:
            counters[status] += 1
        else:
            counters['other'] += 1

        tier_key = f"{tier}"
        if tier_key not in tier_counters:
            tier_counters[tier_key] = {'total': 0, 'success': 0}
        tier_counters[tier_key]['total'] += 1
        if status == 'success':
            tier_counters[tier_key]['success'] += 1

        idx_key = index if qtype != 'multi' else 'multi_index'
        if idx_key not in index_counters:
            index_counters[idx_key] = {'total': 0, 'success': 0}
        index_counters[idx_key]['total'] += 1
        if status == 'success':
            index_counters[idx_key]['success'] += 1

        results.append({
            'id': qid,
            'query': query,
            'type': qtype,
            'tier': tier,
            'index': index,
            'status': status,
            'result_count': result_count,
            'latency_ms': round(latency_ms, 1),
            'error': error,
            'generated_dsl': generated_dsl,
        })

    # Summary
    total = counters['total']
    success = counters['success']
    no_results = counters['no_results']
    valid_dsl = success + no_results  # executed without parse errors

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total queries:       {total}")
    print(f"Success (found data): {success}/{total}  ({success/total*100:.1f}%)")
    print(f"No results (valid DSL but 0 docs): {no_results}/{total}  ({no_results/total*100:.1f}%)")
    print(f"Validation failed:   {counters['validation_failed']}/{total}  ({counters['validation_failed']/total*100:.1f}%)")
    print(f"Execution failed:    {counters['execution_failed']}/{total}  ({counters['execution_failed']/total*100:.1f}%)")
    print(f"Other errors:        {counters['other']}/{total}  ({counters['other']/total*100:.1f}%)")
    print(f"Valid DSL rate:      {valid_dsl}/{total}  ({valid_dsl/total*100:.1f}%)")

    print("\nBy tier:")
    for tier in ['simple', 'medium', 'hard']:
        if tier in tier_counters:
            t = tier_counters[tier]
            pct = t['success'] / t['total'] * 100 if t['total'] else 0
            print(f"  {tier:8s}: {t['success']}/{t['total']} ({pct:.1f}%)")

    print("\nBy index:")
    for idx, counts in sorted(index_counters.items()):
        pct = counts['success'] / counts['total'] * 100 if counts['total'] else 0
        short = idx.replace('moi-', '').replace('-v1', '').replace('-details', '')
        print(f"  {short:35s}: {counts['success']}/{counts['total']} ({pct:.1f}%)")

    # Failures list
    failures = [r for r in results if r['status'] != 'success']
    if failures:
        print(f"\nFailed queries ({len(failures)}):")
        for r in failures:
            print(f"  [{r['id']}] {r['status']} — {r['query'][:60]}")
            if r['error']:
                print(f"       {r['error'][:80]}")

    # Save detailed results
    out_path = f"data/eval_results_v2.json"
    with open(out_path, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'success': success,
                'no_results': no_results,
                'validation_failed': counters['validation_failed'],
                'execution_failed': counters['execution_failed'],
                'success_rate': round(success / total * 100, 1),
                'valid_dsl_rate': round(valid_dsl / total * 100, 1),
            },
            'by_tier': tier_counters,
            'by_index': index_counters,
            'results': results,
        }, f, indent=2)

    print(f"\nDetailed results saved to: {out_path}")
    return success / total * 100


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', default='data/test_corpus_v2.json')
    args = parser.parse_args()

    accuracy = evaluate(args.corpus)
    print(f"\nFinal accuracy: {accuracy:.1f}%")
