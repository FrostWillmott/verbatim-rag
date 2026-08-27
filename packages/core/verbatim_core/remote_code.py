"""Guard for model loaders that execute code from a model repository.

`trust_remote_code=True` runs Python published alongside the model weights, in
this process, with whatever the process can reach — documents, API keys. Without
a `revision` the loader follows the repository's default branch, so the code that
runs today is not necessarily the code that ran yesterday, and an upstream change
needs no action here to take effect.

The loaders keep working without a revision, because pinning one is the
operator's decision and the default models are not ours to pin. What changes is
that the choice stops being silent.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_WARNED: set[tuple[str, str]] = set()


def warn_if_remote_code_is_unpinned(model_ref: str, revision: str | None, loader: str) -> None:
    """Warn once per model when remote code will run from a mutable reference.

    :param model_ref: model id or path being loaded
    :param revision: the pinned revision, or None
    :param loader: the loader being called, for the message
    """
    if revision:
        return

    key = (model_ref, loader)
    if key in _WARNED:
        return
    _WARNED.add(key)

    logger.warning(
        "%s is loading %s with trust_remote_code=True and no pinned revision. "
        "Code from that model repository will execute in this process, and it is "
        "read from the default branch, so it can change without notice. Pass "
        "revision='<commit sha>' to pin it.",
        loader,
        model_ref,
    )
