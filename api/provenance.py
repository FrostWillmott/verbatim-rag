"""What built the index, recorded so a mismatch can be refused instead of served.

`BEY-9`: the shipped indexer and the API disagree about collection and embedding
model, and the disagreement is silent — both models emit 384 dimensions, so the
wrong pairing loads one model's vectors into the other's index and returns
confident nonsense rather than raising.

The marker does not decide which pairing is right; that is still the maintainer's
question. It makes the wrong one loud.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MARKER_NAME = ".verbatim-provenance.json"


def marker_path(index_path: Path) -> Path:
    """Beside the index file, because that is what it describes."""
    return index_path.parent / MARKER_NAME


def record(index_path: Path, *, embedding_model: str, collection: str) -> None:
    """Best effort by design: the index is already written when this runs, and
    losing a finished ingest — minutes of CPU — because a marker file could not
    be written would be the worse failure. An absent marker reads as unknown
    provenance, which is what it is."""
    try:
        _write(index_path, embedding_model=embedding_model, collection=collection)
    except OSError as exc:
        logger.warning(
            "Indexed, but could not record provenance at %s: %s. The API will treat "
            "this index as unknown provenance rather than as a mismatch.",
            marker_path(index_path),
            exc,
        )


def _write(index_path: Path, *, embedding_model: str, collection: str) -> None:
    marker_path(index_path).write_text(
        json.dumps(
            {
                "embedding_model": embedding_model,
                "collection": collection,
                "written_by": "api.ingest",
                "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n"
    )


def read(index_path: Path) -> dict[str, Any] | None:
    """None means unknown provenance, which is not the same as a match."""
    path = marker_path(index_path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def mismatch(index_path: Path, *, embedding_model: str, collection: str) -> str | None:
    """The message to refuse with, or None when there is nothing to refuse."""
    written = read(index_path)
    if written is None:
        return None

    disagreements = [
        f"{name}: index built with {written.get(key)!r}, API configured with {configured!r}"
        for name, key, configured in (
            ("embedding model", "embedding_model", embedding_model),
            ("collection", "collection", collection),
        )
        if written.get(key) != configured
    ]
    if not disagreements:
        return None

    return (
        "The index at "
        f"{index_path} was not built with this configuration — "
        + "; ".join(disagreements)
        + ". Retrieval would return results from vectors this model did not write, "
        "and because the embedding models in play share a dimension it would not "
        "fail: it would answer confidently from the wrong index. Point "
        "EMBEDDING_MODEL and MILVUS_COLLECTION at what built it, or index again."
    )
