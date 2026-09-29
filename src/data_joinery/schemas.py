from collections.abc import Sequence
from typing import TypeVar, cast

from .backends import (
    DataFrameBackend,
    backend_for_frame_type,
    backend_for_schema_type,
    backend_for_value,
)
from .model_schema import ModelSchema, is_pydantic_model, is_schema_model
from .schema_types import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)

T = TypeVar("T")
FrameT = TypeVar("FrameT")


def _require_backend(
    backend: DataFrameBackend | None,
    value_type: type,
    *,
    kind: str,
) -> DataFrameBackend:
    if backend is None:
        raise TypeError(f"No {kind} backend is registered for {value_type.__name__}")
    return backend


class Schema[T]:
    """A backend-neutral schema declaration backed by a dataclass or Pydantic model."""

    def __init__(self, model: type[T]):
        self.model = model
        self._model_schema = ModelSchema.from_model(model)

    @property
    def model_schema(self) -> ModelSchema[T]:
        return self._model_schema

    def native_schema[NativeSchemaT](
        self, schema_type: type[NativeSchemaT]
    ) -> NativeSchemaT:
        """Compile this declaration to the requested native schema type."""
        backend = _require_backend(
            backend_for_schema_type(schema_type), schema_type, kind="schema"
        )
        native_schema = backend.compile_schema(self._model_schema)
        if not isinstance(native_schema, schema_type):
            raise TypeError(
                f"Backend '{backend.name}' returned "
                f"{type(native_schema).__name__}, expected {schema_type.__name__}"
            )
        return native_schema

    def create_dataframe[FrameT](
        self,
        rows: Sequence[T],
        frame_type: type[FrameT],
        **kwargs: object,
    ) -> FrameT:
        """Create a dataframe of the requested type from model instances."""
        backend = _require_backend(
            backend_for_frame_type(frame_type), frame_type, kind="dataframe"
        )
        frame = backend.create_dataframe(rows, self._model_schema, **kwargs)
        if not isinstance(frame, frame_type):
            raise TypeError(
                f"Backend '{backend.name}' returned {type(frame).__name__}, "
                f"expected {frame_type.__name__}"
            )
        return frame

    def coerce_dataframe(
        self, dataframe: FrameT, mode: CoercionMode = "project"
    ) -> FrameT:
        backend = _require_backend(
            backend_for_value(dataframe), type(dataframe), kind="dataframe"
        )
        frame = backend.coerce_dataframe(dataframe, self._model_schema, mode)
        if not isinstance(frame, type(dataframe)):
            raise TypeError(
                f"Backend '{backend.name}' returned {type(frame).__name__}, "
                f"expected {type(dataframe).__name__}"
            )
        return cast(FrameT, frame)

    def __repr__(self) -> str:
        return f"Schema(model={self.model.__name__})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Schema):
            return False
        return self.model == other.model


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
