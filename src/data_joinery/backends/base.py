from collections.abc import Sequence
from importlib import import_module
from importlib.util import find_spec
from typing import Any, Protocol

from ..model_schema import ModelSchema
from ..schema_types import CoercionMode


class DataFrameBackend[FrameT, SchemaT](Protocol):
    """Connect one dataframe class and one native schema class to Data Joinery.

    Backend lookup recognizes subclasses of its registered classes too.
    Implement this protocol, then pass one instance to :func:`register_backend`.
    """

    name: str
    """Unique name used to identify this backend."""

    dataframe_type: type[FrameT]
    """Dataframe class accepted and returned by this backend."""

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
        **kwargs: object,
    ) -> FrameT:
        """Build a frame from model instances using the compiled schema.

        ``kwargs`` carries backend-specific options, such as a Spark session.
        Reject options that this backend does not support.
        """
        ...


_BACKENDS: dict[str, DataFrameBackend[Any, Any]] = {}
_BUILTINS_LOADED = False


def register_backend[FrameT, SchemaT](
    backend: DataFrameBackend[FrameT, SchemaT],
) -> None:
    existing = _BACKENDS.get(backend.name)
    if existing is backend:
        return
    if existing is not None:
        raise ValueError(f"Backend '{backend.name}' is already registered")

    for registered in _BACKENDS.values():
        _raise_for_type_overlap(
            backend.dataframe_type,
            registered.dataframe_type,
            backend,
            registered,
            "dataframe",
        )
        _raise_for_type_overlap(
            backend.schema_type, registered.schema_type, backend, registered, "schema"
        )
    _BACKENDS[backend.name] = backend


def _raise_for_type_overlap(
    candidate_type: type,
    registered_type: type,
    backend: DataFrameBackend[Any, Any],
    registered: DataFrameBackend[Any, Any],
    kind: str,
) -> None:
    if issubclass(candidate_type, registered_type) or issubclass(
        registered_type, candidate_type
    ):
        raise TypeError(
            f"Backend '{backend.name}' has ambiguous {kind} type "
            f"{candidate_type!r} with backend '{registered.name}'"
        )


def _load_builtin_backends() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    if find_spec("pyspark") is not None:
        import_module("data_joinery.backends.spark")
    if find_spec("polars") is not None:
        import_module("data_joinery.backends.polars")


def get_backend(name: str) -> DataFrameBackend[Any, Any]:
    if name not in _BACKENDS:
        _load_builtin_backends()
    try:
        return _BACKENDS[name]
    except KeyError as error:
        raise LookupError(
            f"No dataframe backend named '{name}' is registered"
        ) from error


def backend_for_frame_type(frame_type: type) -> DataFrameBackend[Any, Any] | None:
    if not isinstance(frame_type, type):
        return None
    backend = _find_backend_for_type(frame_type)
    if backend is not None:
        return backend
    _load_builtin_backends()
    return _find_backend_for_type(frame_type)


def backend_for_schema_type(schema_type: type) -> DataFrameBackend[Any, Any] | None:
    if not isinstance(schema_type, type):
        return None
    backend = _find_backend_for_type(schema_type, schema=True)
    if backend is not None:
        return backend
    _load_builtin_backends()
    return _find_backend_for_type(schema_type, schema=True)


def _find_backend_for_type(
    requested_type: type,
    *,
    schema: bool = False,
) -> DataFrameBackend[Any, Any] | None:
    matches = [
        backend
        for backend in _BACKENDS.values()
        if issubclass(
            requested_type,
            backend.schema_type if schema else backend.dataframe_type,
        )
    ]
    if len(matches) > 1:
        names = ", ".join(sorted(backend.name for backend in matches))
        raise LookupError(
            f"Multiple dataframe backends match {requested_type!r}: {names}"
        )
    return matches[0] if matches else None


def backend_for_value(value: object) -> DataFrameBackend[Any, Any] | None:
    return backend_for_frame_type(type(value))
