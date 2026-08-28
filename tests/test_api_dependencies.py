"""Tests for the parts of api.dependencies that can run without the stack.

Constructing the RAG singleton downloads an embedding model and opens Milvus, so
the template-config step is tested through the helper the construction paths call
rather than through them.
"""

import json

import pytest
from fastapi import HTTPException

from api.dependencies import apply_template_config
from verbatim_core.templates import TemplateManager

# Needs the root package installed, not just verbatim-core: this exercises the
# RAG and API surfaces. CI runs these in a separate job — see requires_full_stack
# in pyproject.toml.
pytestmark = pytest.mark.requires_full_stack


class TestApplyTemplateConfig:
    def test_loads_the_mode_from_the_config_file(self, tmp_path):
        config_file = tmp_path / "templates.json"
        config_file.write_text(json.dumps({"current_mode": "question_specific", "strategies": {}}))
        manager = TemplateManager(default_mode="static")

        applied = apply_template_config(manager, config_file)

        assert applied is True
        assert manager.current_mode == "question_specific"

    def test_a_manager_without_an_llm_client_cannot_reach_contextual_mode(self, tmp_path):
        # Why the API-level TemplateManager is not handed to VerbatimRAG: built
        # without an llm_client, its "contextual" strategy is None, so the mode
        # silently falls back to static and every answer's framing changes.
        config_file = tmp_path / "templates.json"
        config_file.write_text(json.dumps({"current_mode": "contextual", "strategies": {}}))
        manager = TemplateManager(default_mode="static")

        apply_template_config(manager, config_file)

        assert manager.strategies["contextual"] is None
        assert manager.current_mode == "static"

    def test_leaves_the_manager_alone_when_the_file_is_absent(self, tmp_path):
        manager = TemplateManager(default_mode="static")

        applied = apply_template_config(manager, tmp_path / "does-not-exist.json")

        assert applied is False
        assert manager.current_mode == "static"


class TestASingletonIsPublishedOnlyOnceItIsConfigured:
    """The globals used to be assigned before the template config was applied, so
    a failure there returned 500 to one caller and left every later request with
    an unconfigured instance that passed the `is None` guard.
    """

    def test_a_failing_template_load_leaves_no_half_built_manager(self, monkeypatch, tmp_path):
        from api import dependencies
        from api.config import APIConfig

        monkeypatch.setattr(dependencies, "_template_manager", None)
        monkeypatch.setattr(
            dependencies,
            "apply_template_config",
            lambda manager, path: (_ for _ in ()).throw(ValueError("bad template file")),
        )

        with pytest.raises(HTTPException):
            dependencies.get_template_manager(
                APIConfig(_env_file=None, templates_path=tmp_path / "templates.json")
            )

        assert dependencies._template_manager is None
