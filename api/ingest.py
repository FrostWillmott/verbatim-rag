"""Put documents into the index this API reads.

The container stack starts with an empty index and the shipped indexer cannot
fill it: `verbatim-rag index` writes to collection `verbatim_rag` with
`all-MiniLM-L6-v2`, while `api/dependencies.py` reads collection `acl` with
granite. Both models emit 384 dimensions, so the mismatch never raises — it
reads as an index that is simply empty. See `BEY-9` in `AUDIT.md`.

This does not pick a winner between those two configurations; that is the
maintainer's call. It sidesteps the choice by building the index through the
API's own factory, so what is written here cannot drift from what the API reads
even if those values change.

Milvus Lite permits a single writer, so the API has to be stopped while this
runs:

    docker compose stop api
    docker compose run --rm --no-deps --entrypoint python api -m api.ingest /app/README.md
    docker compose start api

Indexing is slow on CPU — a single README took just over 17 minutes on an arm64
container. It is working, not hung.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from api.config import APIConfig
from api.dependencies import get_rag_instance
from verbatim_rag.ingestion.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


def collect_documents(paths: list[Path]) -> list[Any]:
    """Read every file, and every file under every directory, given."""
    processor = DocumentProcessor()
    documents: list[Any] = []

    for path in paths:
        if path.is_dir():
            documents.extend(processor.process_directory(str(path)))
        elif path.is_file():
            documents.append(processor.process_file(str(path)))
        else:
            raise FileNotFoundError(f"No such file or directory: {path}")

    return documents


def main(argv: list[str]) -> int:
    logging.basicConfig(level="INFO", force=True)

    if not argv:
        logger.error("usage: python -m api.ingest <file-or-directory> [...]")
        return 2

    documents = collect_documents([Path(arg) for arg in argv])
    if not documents:
        logger.error("Nothing to index: no readable documents in %s", argv)
        return 1

    logger.info("Read %d document(s); indexing into the API's own index", len(documents))
    rag = get_rag_instance(APIConfig())
    rag.index.add_documents(documents)
    logger.info("Indexed %d document(s)", len(documents))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
