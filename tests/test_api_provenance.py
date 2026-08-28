"""What built the index, and what the API does when it disagrees.

`BEY-9` is dangerous because it is silent: both embedding models in play emit
384 dimensions, so the wrong pairing loads one model's vectors into the other's
index and answers confidently instead of raising. These tests pin the three
states that matter — agreement, disagreement, and not knowing.
"""

import json
from pathlib import Path

import pytest

from api import provenance

pytestmark = pytest.mark.requires_full_stack

MODEL = "ibm-granite/granite-embedding-small-english-r2"


def _index(tmp_path: Path) -> Path:
    return tmp_path / "index.db"


class TestMismatch:
    def test_an_unmarked_index_is_unknown_not_wrong(self, tmp_path: Path):
        # Refusing here would break every index written before the marker
        # existed, including one the shipped CLI wrote.
        assert (
            provenance.mismatch(_index(tmp_path), embedding_model=MODEL, collection="acl") is None
        )

    def test_a_matching_marker_permits_the_run(self, tmp_path: Path):
        provenance.record(_index(tmp_path), embedding_model=MODEL, collection="acl")

        assert (
            provenance.mismatch(_index(tmp_path), embedding_model=MODEL, collection="acl") is None
        )

    def test_a_different_model_is_refused_and_both_sides_are_named(self, tmp_path: Path):
        provenance.record(_index(tmp_path), embedding_model="all-MiniLM-L6-v2", collection="acl")

        message = provenance.mismatch(_index(tmp_path), embedding_model=MODEL, collection="acl")

        assert "all-MiniLM-L6-v2" in message
        assert MODEL in message

    def test_a_different_collection_is_refused_too(self, tmp_path: Path):
        provenance.record(_index(tmp_path), embedding_model=MODEL, collection="verbatim_rag")

        message = provenance.mismatch(_index(tmp_path), embedding_model=MODEL, collection="acl")

        assert "verbatim_rag" in message

    def test_an_unreadable_marker_counts_as_unknown(self, tmp_path: Path):
        provenance.marker_path(_index(tmp_path)).write_text("{not json")

        assert (
            provenance.mismatch(_index(tmp_path), embedding_model=MODEL, collection="acl") is None
        )


class TestRecord:
    def test_it_writes_what_built_the_index(self, tmp_path: Path):
        provenance.record(_index(tmp_path), embedding_model=MODEL, collection="acl")

        written = json.loads(provenance.marker_path(_index(tmp_path)).read_text())

        assert written["embedding_model"] == MODEL
        assert written["collection"] == "acl"

    def test_a_marker_it_cannot_write_does_not_lose_the_ingest(self, tmp_path: Path):
        # The index is already written when this runs; failing here would throw
        # away minutes of CPU over a file nobody reads yet.
        provenance.record(tmp_path / "absent" / "index.db", embedding_model=MODEL, collection="acl")
