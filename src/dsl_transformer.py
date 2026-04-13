"""
DSL Transformer

Post-processes generated DSL before ES execution:
- Converts nationality names to numeric codes (e.g. "Qatari" → "634")

This allows training data to use human-readable names, which the model
learns naturally. The transformer handles the name→code conversion at
runtime, making the system maintainable: adding a new nationality means
updating the lookup file, not retraining.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


# Fields that store nationality codes
NATIONALITY_FIELDS = {'person_natcde', 'NAT_CDENUM'}


class DSLTransformer:
    """
    Transforms generated DSL to replace human-readable values with ES-stored values.
    Currently handles: nationality name → numeric code.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._nat_codes: Optional[Dict[str, str]] = None

    def _load_nationality_codes(self) -> Dict[str, str]:
        if self._nat_codes is None:
            path = Path(__file__).parent.parent / 'data' / 'lookups' / 'nationality_codes.json'
            with open(path, 'r', encoding='utf-8') as f:
                self._nat_codes = json.load(f)
        return self._nat_codes

    def transform(self, dsl: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all transformations to a parsed DSL dict.

        Args:
            dsl: Parsed DSL dict (with root 'query' key)

        Returns:
            Transformed DSL dict (original is not mutated)
        """
        import copy
        dsl = copy.deepcopy(dsl)
        dsl['query'] = self._transform_node(dsl.get('query', {}))
        return dsl

    def _transform_node(self, node: Any) -> Any:
        """Recursively walk DSL tree and apply transformations."""
        if isinstance(node, dict):
            # Check if this is a term/match clause on a nationality field
            for clause_type in ('term', 'match', 'match_phrase'):
                if clause_type in node:
                    inner = node[clause_type]
                    for field, value in list(inner.items()):
                        if field in NATIONALITY_FIELDS:
                            inner[field] = self._resolve_nationality(value)
            # Check terms (array) clause
            if 'terms' in node:
                inner = node['terms']
                for field, value in list(inner.items()):
                    if field in NATIONALITY_FIELDS and isinstance(value, list):
                        inner[field] = [self._resolve_nationality(v) for v in value]
            return {k: self._transform_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [self._transform_node(item) for item in node]
        return node

    def _resolve_nationality(self, value: Any) -> str:
        """Convert nationality name to code. Pass through if already a code."""
        if not isinstance(value, str):
            return value
        # Already numeric code — pass through
        if value.isdigit() or (len(value) == 3 and value.isdigit()):
            return value
        codes = self._load_nationality_codes()
        code = codes.get(value)
        if code:
            self.logger.debug(f'Nationality resolved: {value} → {code}')
            return code
        # Unknown nationality name — pass through and let ES handle it
        self.logger.warning(f'Unknown nationality name: {value!r} — passing through unchanged')
        return value
