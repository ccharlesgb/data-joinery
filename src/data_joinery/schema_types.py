"""Compatibility imports; prefer :mod:`data_joinery.schemas.coercion`."""

from .schemas.coercion import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)

__all__ = [
    "CoercionMode",
    "DifferenceKind",
    "SchemaCoercionError",
    "SchemaDiff",
    "SchemaDifference",
]
