"""
Shared fixtures for integration tests that require live ES and LLM connections.

Tests using these fixtures are marked @pytest.mark.accuracy and are skipped
automatically if ES or the LLM server are unreachable.
"""

import json
import logging
import pytest
from pathlib import Path

from src.config import Config
from src.es_client import ESClient
from src.llm_client import VLLMClient
from src.dsl_transformer import DSLTransformer
from src.query_generator import QueryGenerator
from src.query_planner import MultiIndexQueryPlanner
from src.query_executor import MultiIndexExecutor
from src.logger import setup_query_translation_logger

REPO_ROOT = Path(__file__).parent.parent.parent


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "accuracy: end-to-end query accuracy tests (require live ES + LLM)"
    )


# ── connectivity guards ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config():
    cfg = Config()
    cfg.USE_DIRECT_PROMPT = True   # must match LoRA fine-tuning format
    return cfg


@pytest.fixture(scope="session")
def es_client(config):
    client = ESClient(config)
    try:
        client.connect()
        client.check_health()
    except Exception as e:
        pytest.skip(f"Elasticsearch not reachable: {e}")
    return client


@pytest.fixture(scope="session")
def llm_client(config):
    client = VLLMClient(config)
    if not client.verify_model():
        pytest.skip(
            f"LLM server not reachable at {config.VLLM_URL}. "
            "Start inference server first: "
            "venv/bin/mlx_lm.server --model EQuIP-Queries/EQuIP_3B "
            "--adapter-path adapters/equip_moi_v9 --port 1234"
        )
    return client


# ── domain fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def transformer():
    return DSLTransformer(logging.getLogger("test.transformer"))


@pytest.fixture(scope="session")
def logger():
    return setup_query_translation_logger()


@pytest.fixture(scope="session")
def generator(es_client, llm_client, config, logger):
    return QueryGenerator(es_client, llm_client, config, logger)


@pytest.fixture(scope="session")
def planner(llm_client, config, logger):
    return MultiIndexQueryPlanner(llm_client, config, logger)


@pytest.fixture(scope="session")
def executor(es_client, logger):
    return MultiIndexExecutor(es_client, logger)


# ── data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def ground_truth():
    path = REPO_ROOT / "data" / "ground_truth.json"
    if not path.exists():
        pytest.skip("data/ground_truth.json not found. Run scripts/build_ground_truth.py first.")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def corpus():
    path = REPO_ROOT / "data" / "test_corpus_v2.json"
    if not path.exists():
        pytest.skip("data/test_corpus_v2.json not found.")
    with open(path) as f:
        items = json.load(f)
    return {item["id"]: item for item in items}
