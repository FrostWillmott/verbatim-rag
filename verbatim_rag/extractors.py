"""
Compatibility layer: expose extractors from verbatim_core.
"""

from __future__ import annotations

from verbatim_core.extractors import (
    LLMSpanExtractor,
    ModelSpanExtractor,
    SemanticHighlightExtractor,
    SpanExtractionUnavailable,
    SpanExtractor,
)

__all__ = [
    "SpanExtractionUnavailable",
    "SpanExtractor",
    "ModelSpanExtractor",
    "LLMSpanExtractor",
    "SemanticHighlightExtractor",
]
