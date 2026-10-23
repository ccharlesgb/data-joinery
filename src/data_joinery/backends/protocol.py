"""Interface implemented by dataframe backends."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..schemas.coercion_error import CoercionMode
    from ..schemas.model_schema import ModelSchema


class DataFrameBackend[FrameT, SchemaT](Protocol):
    """Connect dataframe classes and one native schema class to Data Joinery.

    Backend lookup recognizes subclasses of its registered classes too.
    Implement this protocol, then pass one instance to :func:`data_joinery.backends.register_backend`.
    """

    name: str
    """Unique name used to identify this backend."""

    dataframe_types: tuple[type[FrameT], ...]
    """Dataframe classes accepted and returned by this backend."""

    schema_type: type[SchemaT]
    """Native schema class returned by :meth:`compile_schema`."""

    def compile_schema(self, schema: ModelSchema[Any]) -> SchemaT:
        """Build a native schema from the model's fields and annotations."""
        ...

    def coerce_dataframe(
        self,
        dataframe: FrameT,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> FrameT:
        """Return a frame that satisfies the model, or raise on a mismatch.

        ``strict`` checks fields and types without changing them. ``project``
        removes extra fields, including nested fields; ``project_top_level``
        removes only extra top-level fields. ``project_cast`` also casts types
        when the native dataframe library permits it. All modes reject missing
        fields. Raise ``SchemaCoercionError`` for schema mismatches.
        """
        ...

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        frame_type: type[FrameT],
        **kwargs: object,
    ) -> FrameT:
        """Build a frame of the requested type using the compiled schema.

        ``kwargs`` carries backend-specific options, such as a Spark session.
        Reject options that this backend does not support.
        """
        ...
