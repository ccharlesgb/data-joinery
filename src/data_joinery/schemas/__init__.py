"""Schema definitions, model adaptation, and coercion diagnostics."""

from .coercion import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)
from .schema import Schema

__all__ = [
    "CoercionMode",
    "DifferenceKind",
    "Schema",
    "SchemaCoercionError",
    "SchemaDiff",
    "SchemaDifference",
]
