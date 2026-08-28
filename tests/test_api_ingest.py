"""The demo stack's ingest entry point.

Its whole reason to exist is that it must write where the API reads (`BEY-9`),
so the load-bearing assertion is that it builds its index through the API's own
factory rather than restating the collection and model a third time. That is
checked here by construction: the factory is replaced, and indexing has to go
through the object it returned.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from api import ingest

pytestmark = pytest.mark.requires_full_stack


class TestCollectDocuments:
    def test_a_missing_path_is_an_error_not_an_empty_corpus(self, tmp_path: Path):
        # Silently indexing nothing is the failure this whole module exists to
        # stop being invisible.
        with pytest.raises(FileNotFoundError):
            ingest.collect_documents([tmp_path / "absent.md"])

    def test_a_readable_file_is_collected(self, tmp_path: Path):
        document = tmp_path / "note.md"
        document.write_text("Verbatim RAG returns exact spans from source documents.\n")

        assert len(ingest.collect_documents([document])) == 1


class TestMain:
    def test_no_arguments_exits_with_a_usage_code(self):
        assert ingest.main([]) == 2

    def test_documents_are_indexed_through_the_api_factory(self, tmp_path: Path, monkeypatch):
        # Own the index path: without it the run reads the developer's .env and
        # writes the provenance marker wherever that points.
        monkeypatch.setenv("INDEX_PATH", str(tmp_path / "index.db"))
        document = tmp_path / "note.md"
        document.write_text("Verbatim RAG returns exact spans from source documents.\n")

        rag = MagicMock()
        monkeypatch.setattr(ingest, "get_rag_instance", lambda config: rag)

        assert ingest.main([str(document)]) == 0
        indexed = rag.index.add_documents.call_args[0][0]
        assert [d.title for d in indexed] == ["note"]

    def test_an_empty_corpus_is_reported_rather_than_indexed(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("INDEX_PATH", str(tmp_path / "index.db"))
        rag = MagicMock()
        monkeypatch.setattr(ingest, "get_rag_instance", lambda config: rag)
        monkeypatch.setattr(ingest, "collect_documents", lambda paths: [])

        assert ingest.main([str(tmp_path)]) == 1
        assert rag.index.add_documents.call_count == 0
