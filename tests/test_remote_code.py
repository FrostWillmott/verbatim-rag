"""Tests for the unpinned-remote-code guard."""

import logging

from verbatim_core import remote_code
from verbatim_core.remote_code import warn_if_remote_code_is_unpinned


def _clear_warned_cache():
    remote_code._WARNED.clear()


class TestWarnIfRemoteCodeIsUnpinned:
    def test_warns_when_no_revision_is_pinned(self, caplog):
        _clear_warned_cache()

        with caplog.at_level(logging.WARNING):
            warn_if_remote_code_is_unpinned("org/model", None, "AutoModel")

        assert "org/model" in caplog.text
        assert "trust_remote_code=True" in caplog.text

    def test_stays_quiet_when_a_revision_is_pinned(self, caplog):
        _clear_warned_cache()

        with caplog.at_level(logging.WARNING):
            warn_if_remote_code_is_unpinned("org/model", "abc123", "AutoModel")

        assert caplog.text == ""

    def test_warns_only_once_per_model_and_loader(self, caplog):
        _clear_warned_cache()

        with caplog.at_level(logging.WARNING):
            warn_if_remote_code_is_unpinned("org/model", None, "AutoModel")
            warn_if_remote_code_is_unpinned("org/model", None, "AutoModel")

        assert caplog.text.count("org/model") == 1

    def test_a_different_loader_warns_separately(self, caplog):
        _clear_warned_cache()

        with caplog.at_level(logging.WARNING):
            warn_if_remote_code_is_unpinned("org/model", None, "AutoModel")
            warn_if_remote_code_is_unpinned("org/model", None, "AutoConfig")

        assert caplog.text.count("org/model") == 2
