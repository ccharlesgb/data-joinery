"""Backend registration, lazy built-in discovery, and lookup."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import Any

from .protocol import DataFrameBackend

_BACKENDS: dict[str, DataFrameBackend[Any, Any]] = {}
_BUILTINS_LOADED = False


def register_backend[FrameT, SchemaT](
    backend: DataFrameBackend[FrameT, SchemaT],
) -> None:
    """Register a backend with a unique name and non-overlapping types.

    Args:
        backend: Implementation of the dataframe backend protocol.

    Raises:
        ValueError: The name is already used or no dataframe types are supplied.
        TypeError: Frame or schema types overlap another backend's types.
    """
    existing = _BACKENDS.get(backend.name)
    if existing is backend:
        return
    if existing is not None:
        raise ValueError(f"Backend '{backend.name}' is already registered")

    if not backend.dataframe_types:
        raise ValueError(f"Backend '{backend.name}' must register a dataframe type")

    for registered in _BACKENDS.values():
        for candidate_type in backend.dataframe_types:
            for registered_type in registered.dataframe_types:
                _raise_for_type_overlap(
                    candidate_type,
                    registered_type,
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
    """Find a backend by name, discovering installed built-ins if needed.

    Args:
        name: Registered backend name.

    Raises:
        LookupError: No registered or installed backend has this name.
    """
    if name not in _BACKENDS:
        _load_builtin_backends()
    try:
        return _BACKENDS[name]
    except KeyError as error:
        raise LookupError(
            f"No dataframe backend named '{name}' is registered"
        ) from error


def backend_for_frame_type(frame_type: type) -> DataFrameBackend[Any, Any] | None:
    """Find the backend owning a frame class or subclass, or return None."""
    if not isinstance(frame_type, type):
        return None
    backend = _find_backend_for_type(frame_type)
    if backend is not None:
        return backend
    _load_builtin_backends()
    return _find_backend_for_type(frame_type)


def backend_for_schema_type(schema_type: type) -> DataFrameBackend[Any, Any] | None:
    """Find the backend owning a native schema class or subclass, or return None."""
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
        if (
            issubclass(requested_type, backend.schema_type)
            if schema
            else any(
                issubclass(requested_type, frame_type)
                for frame_type in backend.dataframe_types
            )
        )
    ]
    if len(matches) > 1:
        names = ", ".join(sorted(backend.name for backend in matches))
        raise LookupError(
            f"Multiple dataframe backends match {requested_type!r}: {names}"
        )
    return matches[0] if matches else None


def backend_for_value(value: object) -> DataFrameBackend[Any, Any] | None:
    """Find the backend owning a dataframe instance, or return None."""
    return backend_for_frame_type(type(value))
