#!/usr/bin/env python3
"""
Quick test script to verify Phase 4 MVP with real Elasticsearch and vLLM

Usage:
    python test_real_query.py
"""

import json
from src.config import Config
from src.es_client import ESClient
from src.llm_client import VLLMClient
from src.query_generator import QueryGenerator
from src.logger import setup_query_translation_logger


def test_real_query():
    """Test with real services and real data"""

    print("=" * 80)
    print("PHASE 4 MVP - REAL DATA TEST")
    print("=" * 80)

    # Initialize components
    print("\n1. Initializing components...")
    config = Config()
    logger = setup_query_translation_logger()

    print(f"   - Elasticsearch: {config.ES_HOST}:{config.ES_PORT}")
    print(f"   - vLLM: {config.VLLM_URL}")
    print(f"   - Model: {config.VLLM_MODEL}")

    # Connect to Elasticsearch
    print("\n2. Connecting to Elasticsearch...")
    es_client = ESClient(config)
    es_client.connect()
    print("   ✓ Connected")

    # Initialize LLM client
    print("\n3. Connecting to LLM...")
    llm_client = VLLMClient(config)
    print("   ✓ Connected")

    # Create generator
    generator = QueryGenerator(es_client, llm_client, config, logger)

    # Test queries
    test_cases = [
        {
            "query": "Find all Qatari nationals",
            "index": "person_details",
            "description": "Simple nationality filter"
        },
        {
            "query": "Show me people named Peter",
            "index": "person_details",
            "description": "Name search (English)"
        },
        {
            "query": "Find female residents",
            "index": "person_details",
            "description": "Gender and person type filter"
        }
    ]

    print("\n" + "=" * 80)
    print("RUNNING TEST QUERIES")
    print("=" * 80)

    results_summary = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['description']}")
        print(f"Query: \"{test['query']}\"")
        print(f"Index: {test['index']}")
        print("-" * 80)

        result = generator.generate_query(test['query'], test['index'])

        # Display results
        status = result['status']
        if status == 'success':
            print(f"✓ Status: SUCCESS")
            print(f"  - Results: {result.get('result_count', 0)} documents")
            print(f"  - LLM Latency: {result['llm_latency_ms']:.1f} ms")
            print(f"  - ES Latency: {result.get('es_latency_ms', 0):.1f} ms")
            print(f"  - Total Latency: {result['total_latency_ms']:.1f} ms")

            # Show generated DSL
            if result.get('generated_dsl'):
                print(f"\n  Generated DSL:")
                try:
                    dsl = json.loads(result['generated_dsl'])
                    print(f"  {json.dumps(dsl, indent=4)}")
                except:
                    print(f"  {result['generated_dsl']}")

            # Show sample results
            if result.get('results'):
                hits = result['results'].get('hits', {}).get('hits', [])
                if hits:
                    print(f"\n  Sample result:")
                    print(f"  {json.dumps(hits[0]['_source'], indent=4)}")
        else:
            print(f"✗ Status: {status}")
            if result.get('error'):
                print(f"  Error: {result['error']}")

        results_summary.append({
            'query': test['query'],
            'status': status,
            'result_count': result.get('result_count', 0),
            'is_valid_json': result.get('is_valid_json', False)
        })

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results_summary)
    successful = sum(1 for r in results_summary if r['status'] == 'success')
    valid_dsl = sum(1 for r in results_summary if r['is_valid_json'])

    print(f"\nTotal queries: {total}")
    print(f"Successful: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"Valid DSL: {valid_dsl}/{total} ({valid_dsl/total*100:.1f}%)")

    print(f"\nDetailed results logged to: logs/query_translations.jsonl")

    return results_summary


if __name__ == "__main__":
    try:
        results = test_real_query()
        print("\n✓ Test completed successfully!")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
