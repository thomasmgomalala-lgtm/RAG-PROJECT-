from contextlib import contextmanager

from app.routers import api
from app.schemas import QueryRequest
from app.services.ingestion import extract_html_pages, split_text
from app.services.llm import ExtractiveProvider
from app.services import retrieval
from app.services.retrieval import tokenize


def test_split_text_overlaps_and_preserves_content():
    words = [f"word{i}" for i in range(500)]
    chunks = split_text(" ".join(words), chunk_size=100, overlap=20)
    assert len(chunks) == 6
    assert chunks[0].split()[-20:] == chunks[1].split()[:20]
    assert chunks[-1].split()[-1] == "word499"


def test_html_extraction_preserves_page_breaks_and_ignores_scripts():
    html = b"<html><body><p>Page one</p><hr style='page-break-after:always'><p>Page two</p><script>hidden text</script></body></html>"
    assert extract_html_pages(html) == [(1, "Page one"), (2, "Page two")]


def test_tokenize_handles_currency_and_punctuation():
    assert tokenize("Tesla revenue: $97.69 billion in 2024") == ["tesla", "revenue", "97", "69", "billion", "in", "2024"]
    assert retrieval._search_terms("Tesla's revenues") == ["tesla", "revenue"]


def test_retrieval_matches_inflections_and_ranks_relevant_passage(monkeypatch):
    rows = [
        {
            "document_id": "irrelevant",
            "filename": "tesla-2025-10k.html",
            "page": 90,
            "content": "Tesla reported in 2025 that related-party transactions were immaterial.",
        },
        {
            "document_id": "relevant",
            "filename": "tesla-2025-10k.html",
            "page": 31,
            "content": "Tesla delivered 1.66 million consumer vehicles in 2025.",
        },
    ]

    class FakeDatabase:
        def execute(self, query):
            return self

        def fetchall(self):
            return rows

    @contextmanager
    def fake_connection():
        yield FakeDatabase()

    monkeypatch.setattr(retrieval, "connection", fake_connection)
    passages = retrieval.retrieve("How many deliveries did Tesla make in 2025?", top_k=2)

    assert passages[0]["document_id"] == "relevant"
    assert passages[0]["page"] == 31


def test_retrieval_boosts_exact_phrases_and_deduplicates_passages(monkeypatch):
    revenue = {
        "document_id": "revenue",
        "filename": "tesla-2025-10k.html",
        "page": 36,
        "content": "Tesla total revenues were $94,827 million in 2025 and $97,690 million in 2024.",
    }
    rows = [
        {
            "document_id": "footnote",
            "filename": "tesla-2025-10k.html",
            "page": 59,
            "content": "Tesla reported vehicle guarantee liabilities as of December 31, 2025 and 2024.",
        },
        revenue,
        {**revenue, "document_id": "revenue-copy", "filename": "tesla-2025-10k.pdf"},
    ]

    class FakeDatabase:
        def execute(self, query):
            return self

        def fetchall(self):
            return rows

    @contextmanager
    def fake_connection():
        yield FakeDatabase()

    monkeypatch.setattr(retrieval, "connection", fake_connection)
    passages = retrieval.retrieve("What were Tesla's total revenues in 2025 and 2024?", top_k=3)

    assert passages[0]["document_id"] == "revenue"
    assert [passage["document_id"] for passage in passages] == ["revenue", "footnote"]


def test_fallback_provider_is_explicit_when_no_context():
    answer = ExtractiveProvider().answer("What was revenue?", [])
    assert "couldn't find a relevant passage" in answer


def test_query_returns_citations_when_llm_provider_fails(monkeypatch):
    passage = {
        "document_id": "doc-1",
        "filename": "tesla-2025-10k.html",
        "page": 31,
        "content": "Total revenues were $94.83 billion.",
        "score": 1.0,
    }

    class FailingProvider:
        def answer(self, question, passages):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(api, "retrieve", lambda question, top_k: [passage])
    monkeypatch.setattr(api, "get_provider", FailingProvider)
    response = api.query_documents(QueryRequest(question="What was revenue?"))

    assert response.provider == "retrieval-only"
    assert "configured LLM failed" in response.answer
    assert response.citations[0].filename == passage["filename"]
    assert response.citations[0].page == passage["page"]