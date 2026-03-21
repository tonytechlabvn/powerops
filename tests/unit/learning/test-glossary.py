"""Unit tests for backend.learning.glossary."""
from __future__ import annotations

import pytest

from backend.learning.glossary import get_concept, list_concepts, search_concepts


# ---------------------------------------------------------------------------
# get_concept
# ---------------------------------------------------------------------------


def test_get_concept_returns_valid_state() -> None:
    concept = get_concept("state")
    assert concept is not None
    assert concept["term"] == "state"
    assert "one_line" in concept
    assert "explanation" in concept


def test_get_concept_case_insensitive() -> None:
    lower = get_concept("state")
    upper = get_concept("STATE")
    assert lower is not None
    assert upper is not None
    assert lower["term"] == upper["term"]


def test_get_concept_unknown_returns_none() -> None:
    result = get_concept("this_concept_does_not_exist_xyz")
    assert result is None


def test_get_concept_partial_prefix_match() -> None:
    # "work" should prefix-match "workspace"
    result = get_concept("work")
    assert result is not None


# ---------------------------------------------------------------------------
# list_concepts
# ---------------------------------------------------------------------------


def test_list_concepts_returns_20() -> None:
    concepts = list_concepts()
    assert len(concepts) == 20


def test_list_concepts_each_has_term_and_one_line() -> None:
    for entry in list_concepts():
        assert "term" in entry
        assert "one_line" in entry
        assert len(entry["term"]) > 0
        assert len(entry["one_line"]) > 0


def test_list_concepts_no_explanation_field() -> None:
    """list_concepts should return summary only — no full explanation."""
    for entry in list_concepts():
        assert "explanation" not in entry


# ---------------------------------------------------------------------------
# search_concepts
# ---------------------------------------------------------------------------


def test_search_concepts_finds_workspace() -> None:
    results = search_concepts("work")
    terms = [r["term"] for r in results]
    assert "workspace" in terms


def test_search_concepts_returns_list_of_dicts() -> None:
    results = search_concepts("state")
    assert isinstance(results, list)
    for r in results:
        assert "term" in r
        assert "one_line" in r


def test_search_concepts_empty_query_returns_all() -> None:
    # Empty string is in every haystack — all concepts match
    results = search_concepts("")
    assert len(results) == 20


def test_search_concepts_no_match_returns_empty() -> None:
    results = search_concepts("zzz_no_match_xyz_abc")
    assert results == []
