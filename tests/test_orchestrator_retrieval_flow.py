from __future__ import annotations

from services.routers.orchestrator import _rank_context_evidence


class StubClient:
    def __init__(self) -> None:
        self.calls = []
        self.responses = self._Responses(self)

    class _Responses:
        def __init__(self, parent: "StubClient") -> None:
            self.parent = parent

        def create(self, *args, **kwargs):
            self.parent.calls.append(kwargs)
            return type(
                "Response",
                (),
                {"output_text": '{"ranked_ids": ["chunk-2", "chunk-1"], "reasons": ["more direct", "less direct"]}'},
            )()


def test_rank_context_evidence_orders_candidates_with_llm_feedback() -> None:
    client = StubClient()
    chunks = [
        {"id": "chunk-1", "document": "The company increased revenue in the fourth quarter."},
        {"id": "chunk-2", "document": "Management commentary explains the revenue growth drivers."},
    ]

    ranked = _rank_context_evidence(
        question="What drove revenue growth?",
        rewritten_queries=["revenue growth drivers", "company revenue performance"],
        expanded_terms=["revenue", "growth"],
        candidate_chunks=chunks,
        client=client,
        n_results=2,
    )

    assert [item["id"] for item in ranked] == ["chunk-2", "chunk-1"]
    assert ranked[0]["reason"] == "more direct"
