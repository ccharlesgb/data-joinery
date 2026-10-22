"""Compatibility imports; prefer :mod:`data_joinery.schemas.model_schema`."""

from .schemas.model_schema import (
    ModelField,
    ModelSchema,
    get_model_fields,
    is_pydantic_model,
    is_schema_model,
)

__all__ = [
    "ModelField",
    "ModelSchema",
    "get_model_fields",
    "is_pydantic_model",
    "is_schema_model",
]
