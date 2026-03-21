"""Glossary lookup functions for Terraform concepts.

Concept data lives in glossary-concepts.py (loaded via importlib because
kebab-case filenames cannot be imported with standard dotted-path syntax).

Public API:
    CONCEPTS        — full dict of all concept entries
    CONCEPT_NAMES   — ordered list of term strings
    get_concept()   — lookup by term (case-insensitive, partial match)
    list_concepts() — all concepts as [{term, one_line}]
    search_concepts() — full-text search across term/explanation
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load kebab-case data module (glossary-concepts.py)
# ---------------------------------------------------------------------------

_MODULE_NAME = "backend.learning.glossary_concepts"
_MODULE_FILE = Path(__file__).parent / "glossary-concepts.py"


def _load_concepts_module():
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MODULE_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate glossary-concepts.py at {_MODULE_FILE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_data = _load_concepts_module()

CONCEPTS: dict[str, dict] = _data.CONCEPTS
CONCEPT_NAMES: list[str] = _data.CONCEPT_NAMES


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_concept(term: str) -> dict | None:
    """Return full concept dict for the given term (case-insensitive).

    Tries exact match first, then prefix match.
    Returns None if no match found.
    """
    normalised = term.strip().lower()
    if normalised in CONCEPTS:
        return CONCEPTS[normalised]
    for key, concept in CONCEPTS.items():
        if key.startswith(normalised):
            return concept
    return None


def list_concepts() -> list[dict]:
    """Return all concepts as [{term, one_line}] — no explanation or example."""
    return [
        {"term": v["term"], "one_line": v["one_line"]}
        for v in CONCEPTS.values()
    ]


def search_concepts(query: str) -> list[dict]:
    """Full-text search across term, one_line, and explanation.

    Returns list of matching concepts as [{term, one_line}].
    """
    q = query.strip().lower()
    results: list[dict] = []
    for concept in CONCEPTS.values():
        haystack = (
            concept["term"] + " "
            + concept["one_line"] + " "
            + concept["explanation"]
        ).lower()
        if q in haystack:
            results.append({"term": concept["term"], "one_line": concept["one_line"]})
    return results
