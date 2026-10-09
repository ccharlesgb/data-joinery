from collections.abc import Sequence
from typing import Any, TypeVar, cast

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
    backend: DataFrameBackend[Any, Any] | None,
    value_type: type,
    *,
    kind: str,
) -> DataFrameBackend[Any, Any]:
    if backend is None:
        raise TypeError(
            f"No {kind} backend is registered for {value_type.__name__}. "
            "Use a supported type or register a backend for it."
        )
    return backend


class Schema[T]:
    """Define DataFrame fields from a dataclass or Pydantic model.

    Args:
        model: Class whose fields define the schema.

    Attributes:
        model: Class used to define the schema.
        model_schema: Parsed fields from the model.
    """

    def __init__(self, model: type[T]):
        self.model = model
        self._model_schema = ModelSchema.from_model(model)

    @property
    def model_schema(self) -> ModelSchema[T]:
        """Return the fields parsed from the model."""
        return self._model_schema

    def native_schema[NativeSchemaT](
        self, schema_type: type[NativeSchemaT]
    ) -> NativeSchemaT:
        """Return this schema in a backend's native schema type.

        Args:
            schema_type: Native schema class to create, such as a Spark
                ``StructType`` or Polars ``Schema``.

        Returns:
            The compiled native schema.
        """
        backend = _require_backend(
            backend_for_schema_type(schema_type), schema_type, kind="schema"
        )
        native_schema = backend.compile_schema(self._model_schema)
        if not isinstance(native_schema, schema_type):
            raise TypeError(
                f"Backend '{backend.name}' returned schema type "
                f"{type(native_schema).__name__}; expected {schema_type.__name__}. "
                "Fix the backend's compile_schema() result."
            )
        return native_schema

    def create_dataframe[FrameT](
        self,
        rows: Sequence[T],
        frame_type: type[FrameT],
        **kwargs: object,
    ) -> FrameT:
        """Create a DataFrame from model instances.

        Args:
            rows: Model instances to include in the DataFrame.
            frame_type: DataFrame class to create.
            **kwargs: Extra options passed to the DataFrame backend.

        Returns:
            A DataFrame of the requested type.
        """
        backend = _require_backend(
            backend_for_frame_type(frame_type), frame_type, kind="dataframe"
        )
        frame = backend.create_dataframe(rows, self._model_schema, **kwargs)
        if not isinstance(frame, frame_type):
            raise TypeError(
                f"Backend '{backend.name}' returned DataFrame type "
                f"{type(frame).__name__}; expected {frame_type.__name__}. "
                "Fix the backend's create_dataframe() result."
            )
        return frame

    def coerce_dataframe(
        self, dataframe: FrameT, mode: CoercionMode = "project"
    ) -> FrameT:
        """Validate and adapt a DataFrame to this schema.

        ``project`` removes extra fields, including nested fields. Use
        ``strict`` to reject extras, ``project_top_level`` to require nested
        fields to match, or ``project_cast`` to also cast field types.
        Missing fields cause an error in every mode.

        Args:
            dataframe: DataFrame to validate and adapt.
            mode: Schema coercion mode. Defaults to ``project``.

        Returns:
            A DataFrame of the same backend type.

        Raises:
            SchemaCoercionError: If the DataFrame cannot match the schema.
        """
        backend = _require_backend(
            backend_for_value(dataframe), type(dataframe), kind="dataframe"
        )
        try:
            frame = backend.coerce_dataframe(dataframe, self._model_schema, mode)
        except SchemaCoercionError as error:
            raise SchemaCoercionError(
                error.mode,
                error.violations,
                location=f"Schema '{self.model.__name__}'",
            ) from None
        if not isinstance(frame, type(dataframe)):
            raise TypeError(
                f"Backend '{backend.name}' returned DataFrame type "
                f"{type(frame).__name__}; expected {type(dataframe).__name__}. "
                "Fix the backend's coerce_dataframe() result."
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
