"""Schema definitions, model adaptation, and coercion diagnostics."""

from .coercion_error import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)
from .joinery_model import JoineryModel, column, Column
from .schema import Schema

__all__ = [
    "CoercionMode",
    "DifferenceKind",
    "JoineryModel",
    "Schema",
    "SchemaCoercionError",
    "SchemaDiff",
    "SchemaDifference",
    "column",
    "Column"
]
