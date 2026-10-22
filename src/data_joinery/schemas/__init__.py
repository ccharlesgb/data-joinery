"""Schema definitions, model adaptation, and coercion diagnostics."""

from .coercion import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)
from .model_schema import is_pydantic_model, is_schema_model
from .schema import Schema

__all__ = [
    "CoercionMode",
    "DifferenceKind",
    "Schema",
    "SchemaCoercionError",
    "SchemaDiff",
    "SchemaDifference",
    "is_pydantic_model",
    "is_schema_model",
]
