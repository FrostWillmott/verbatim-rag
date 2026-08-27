"""Test doubles for the RAG pipeline.

The pipeline's real dependencies are Milvus, an embedding model and an LLM, none
of which belong in a unit test. `VerbatimRAG` takes all three through its
constructor, so the doubles below plug into the same seams the production code
uses — no patching, nothing monkeyed at import time.

Kept honest on the one thing that matters: `FakeSpanExtractor` returns text that
really occurs in the document it is given, because `_verify_spans` drops spans
that do not, and a double that returned invented text would let a broken
pipeline pass.
"""

from __future__ import annotations

from typing import Any

from verbatim_rag.vector_stores.base import SearchResult


class FakeIndex:
    """Stands in for VerbatimIndex over a real vector store.

    Stores whatever it is given and answers queries by naive substring overlap,
    which is enough to tell "the corpus reached retrieval" from "it did not".
    """

    def __init__(self) -> None:
        self.documents: list[Any] = []
        self.query_calls: list[dict[str, Any]] = []

    def add_documents(self, documents: list[Any]) -> None:
        self.documents.extend(documents)

    def query(
        self,
        text: str,
        k: int = 5,
        filter: str | None = None,
        hybrid_weights: dict[str, float] | None = None,
        rrf_k: int = 60,
        search_params: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        self.query_calls.append({"text": text, "k": k, "filter": filter})

        terms = {w.lower().strip("?.,") for w in text.split() if len(w) > 3}
        scored = []
        for doc in self.documents:
            content = _document_text(doc)
            overlap = sum(1 for t in terms if t in content.lower())
            if overlap:
                scored.append((overlap, doc, content))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchResult(
                id=str(getattr(doc, "id", index)),
                score=float(overlap),
                metadata={"title": getattr(doc, "title", ""), "source": getattr(doc, "source", "")},
                text=content,
            )
            for index, (overlap, doc, content) in enumerate(scored[:k])
        ]


class FakeSpanExtractor:
    """Returns the first sentence of each retrieved document, verbatim.

    Verbatim matters: the real pipeline verifies every span against its source
    document and silently drops the ones that do not match, so a double that
    invented text would produce an empty answer and hide a regression.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def extract_spans(self, question: str, search_results: list[Any]) -> dict[str, list[str]]:
        self.calls.append(question)
        spans: dict[str, list[str]] = {}
        for result in search_results:
            text = getattr(result, "text", "")
            first = text.split(". ")[0]
            if first and not first.endswith("."):
                first = f"{first}."
            spans[text] = [first] if first in text else []
        return spans


class FakeLLMClient:
    """Placeholder for the constructor argument.

    A static template manager and an injected extractor mean nothing in the
    happy path calls an LLM; this exists so the test does not depend on
    OPENAI_API_KEY being present in the environment.
    """

    def __init__(self, model: str = "fake-model") -> None:
        self.model = model


def _document_text(document: Any) -> str:
    for attribute in ("raw_content", "content", "text"):
        value = getattr(document, attribute, None)
        if value:
            return str(value)
    return ""
