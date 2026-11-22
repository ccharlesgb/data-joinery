"""Schema definitions, model adaptation, and coercion diagnostics."""

from .coercion import CoercionMode
from .coercion_error import SchemaCoercionError
from .joinery_model import Column, JoineryModel, column
from .schema import Schema
from .schema_diff import (
    DifferenceKind,
    SchemaDiff,
    SchemaDifference,
)

__all__ = [
    "CoercionMode",
    "Column",
    "DifferenceKind",
    "JoineryModel",
    "Schema",
    "SchemaCoercionError",
    "SchemaDiff",
    "SchemaDifference",
    "column",
]
