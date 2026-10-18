from collections import Counter, defaultdict

from core import Paper, _abstract_from_inverted_index, _tokens, evidence_quote_is_exact, rank_candidates


def paper(identifier, title, abstract, year=2024, citations=10):
    return Paper(
        openalex_id=identifier,
        title=title,
        year=year,
        authors=["A. Researcher"],
        doi=None,
        pmid=None,
        cited_by_count=citations,
        work_type="article",
        abstract=abstract,
        referenced_works=[],
        source_url=identifier,
    )


def test_rebuilds_abstract_in_order():
    index = {"immune": [1], "Melanoma": [0], "cells": [2]}
    assert _abstract_from_inverted_index(index) == "Melanoma immune cells"


def test_tokenizer_removes_stopwords_and_punctuation():
    assert _tokens("What are the T-cells in melanoma?") == {"cells", "melanoma"}


def test_evidence_quote_must_be_an_exact_abstract_substring():
    abstract = "Single-cell RNA sequencing identified distinct immune cell states."
    assert evidence_quote_is_exact("distinct immune cell states", abstract)
    assert not evidence_quote_is_exact("improved patient survival", abstract)
    assert not evidence_quote_is_exact("", abstract)


def test_multi_seed_connection_improves_rank():
    seeds = [
        paper("S1", "Melanoma immune atlas", "single cell melanoma immune response"),
        paper("S2", "Treatment response", "melanoma treatment response cells"),
    ]
    bridge = paper("B", "Melanoma single-cell response", "single cell melanoma treatment response")
    isolated = paper("I", "Melanoma single-cell response", "single cell melanoma treatment response")
    paths = defaultdict(set, {"B": {"Cites seed 1", "Cites seed 2"}, "I": {"Question search match"}})
    rows = rank_candidates(
        "single cell melanoma treatment response",
        seeds,
        [isolated, bridge],
        paths,
        Counter(),
    )
    assert rows[0]["openalex_id"] == "B"
    assert rows[0]["signals"]["seed_connections"] == 2


def test_shared_reference_path_is_explained():
    seed = paper("S", "Seed", "immune cells")
    candidate = paper("C", "Candidate", "immune cells")
    paths = defaultdict(set)
    rows = rank_candidates("immune cells", [seed], [candidate], paths, Counter({"C": 2}))
    assert "Referenced by 2 seed paper(s)" in rows[0]["discovery_paths"]

