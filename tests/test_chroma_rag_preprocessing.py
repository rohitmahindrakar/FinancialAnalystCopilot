from services.routers.chroma import _build_query_variants, _merge_query_results


def test_build_query_variants_includes_rewrites_and_expansions() -> None:
    variants = _build_query_variants(
        "show revenue",
        rewritten_queries=["revenue trend", "actual revenue"],
        expanded_terms=["budget", "forecast"],
    )

    assert variants[0] == "show revenue"
    assert "revenue trend" in variants
    assert "actual revenue" in variants
    assert "show revenue budget forecast" in variants


def test_merge_query_results_reranks_candidates_by_relevance() -> None:
    merged = _merge_query_results(
        {
            "ids": [["doc-1", "doc-2"], ["doc-1", "doc-3"]],
            "documents": [
                ["Revenue performance and actuals summary", "Margin guidance overview"],
                ["Revenue performance and actuals summary", "Budget forecast commentary"],
            ],
            "distances": [[0.25, 0.9], [0.15, 0.55]],
        },
        query_variants=["revenue", "forecast"],
        rerank=True,
        n_results=2,
    )

    assert merged[0]["id"] == "doc-1"
    assert merged[0]["relevance_score"] >= merged[1]["relevance_score"]
