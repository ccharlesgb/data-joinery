"""Compatibility coverage for the former context module."""

from data_joinery import Context as ExportedContext
from data_joinery.context import Context, inspect_context_type
from data_joinery.dependencies import (
    Context as LegacyContext,
)
from data_joinery.dependencies import (
    inspect_context_type as legacy_inspect_context_type,
)


def test_legacy_context_is_canonical_context():
    assert LegacyContext is Context


def test_legacy_inspection_is_canonical_inspection():
    assert legacy_inspect_context_type is inspect_context_type


def test_root_context_is_canonical_context():
    assert ExportedContext is Context
