"""End-to-end cover for the RAG path: documents in, cited answer out.

This is the surface the test-quality audit reported as having no tests at all.
It runs against doubles for the index, the span extractor and the LLM client —
all three are constructor arguments of VerbatimRAG — so it needs no Milvus, no
embedding model and no API key.
"""

import pytest

from tests.fakes import FakeIndex, FakeLLMClient, FakeSpanExtractor
from verbatim_rag.core import VerbatimRAG
from verbatim_rag.schema import DocumentSchema

# Needs the root package installed, not just verbatim-core: this exercises the
# RAG and API surfaces. CI runs these in a separate job — see requires_full_stack
# in pyproject.toml.
pytestmark = pytest.mark.requires_full_stack

CORPUS = [
    (
        "Retrieval",
        "Dense retrieval maps queries and passages into one vector space. "
        "It was popularised by DPR in 2020.",
    ),
    (
        "Evaluation",
        "Recall at k measures how often a relevant passage appears in the top k. "
        "It ignores the order of the results entirely.",
    ),
    (
        "Unrelated",
        "The cafeteria serves lunch between twelve and two. Bring your badge.",
    ),
]


@pytest.fixture
def rag():
    index = FakeIndex()
    system = VerbatimRAG(
        index=index,
        k=3,
        template_mode="static",
        extractor=FakeSpanExtractor(),
        llm_client=FakeLLMClient(),
    )
    for title, content in CORPUS:
        system.add_document(DocumentSchema(title=title, content=content))
    return system


class TestIngestion:
    def test_documents_reach_the_index(self, rag):
        assert len(rag.index.documents) == 3

    def test_add_document_returns_the_id_it_stored(self, rag):
        document = DocumentSchema(title="Extra", content="A fourth document.")

        returned = rag.add_document(document)

        assert returned == rag.index.documents[-1].id

    def test_content_survives_the_schema_conversion(self, rag):
        stored = {doc.raw_content for doc in rag.index.documents}

        assert any("Dense retrieval maps queries" in text for text in stored)


class TestQuery:
    def test_answer_quotes_the_source_verbatim(self, rag):
        response = rag.query("What is dense retrieval?")

        assert "Dense retrieval maps queries and passages into one vector space." in response.answer

    def test_every_citation_points_at_text_present_in_its_document(self, rag):
        response = rag.query("What is dense retrieval?")

        assert response.structured_answer.citations
        for citation in response.structured_answer.citations:
            document = response.documents[citation.doc_index]
            assert citation.text in document.content

    def test_every_highlight_lands_on_its_own_offsets(self, rag):
        # The offsets are what the UI uses to paint the source panel; if they
        # drift, the product highlights the wrong words while still looking fine.
        response = rag.query("What is dense retrieval?")

        highlighted = [
            (document.content[h.start : h.end], h.text)
            for document in response.documents
            for h in document.highlights
        ]
        assert highlighted
        for sliced, claimed in highlighted:
            assert sliced == claimed

    def test_retrieval_receives_the_configured_k(self, rag):
        rag.query("What is dense retrieval?")

        assert rag.index.query_calls[-1]["k"] == 3

    def test_an_explicit_k_overrides_the_default(self, rag):
        rag.query("What is dense retrieval?", k=1)

        assert rag.index.query_calls[-1]["k"] == 1

    def test_the_question_reaches_the_extractor(self, rag):
        rag.query("What is recall at k?")

        assert rag.extractor.calls == ["What is recall at k?"]

    def test_a_question_the_corpus_cannot_answer_yields_no_citations(self, rag):
        response = rag.query("What is the airspeed velocity of a swallow?")

        assert response.structured_answer.citations == []
