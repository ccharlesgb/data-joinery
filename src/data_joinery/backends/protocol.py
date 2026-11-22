"""Interface implemented by dataframe backends."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..schemas.coercion import CoercionMode
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
        """Validate or adapt a frame to a model schema.

        ``strict`` requires matching fields and types and preserves the input's
        values and column order. Projection modes return columns in model
        order. ``project_top_level`` removes extra top-level columns and
        requires matching nested fields. ``project`` also removes extra
        nested fields. ``project_cast`` projects recursively and uses native
        casting rules. Lazy frames may report value-dependent cast failures
        when they execute.

        Args:
            dataframe: Input frame.
            schema: Target model schema.
            mode: Which validation and projection rules to apply.

        Returns:
            A frame of the same type as the input.

        Raises:
            SchemaCoercionError: The frame has schema violations for the mode.
                All modes reject missing fields.
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
