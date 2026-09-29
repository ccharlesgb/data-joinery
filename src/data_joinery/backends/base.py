from collections.abc import Sequence
from importlib import import_module
from importlib.util import find_spec
from typing import Any, Protocol

from ..model_schema import ModelSchema
from ..schema_types import CoercionMode


class DataFrameBackend(Protocol):
    name: str

    @property
    def dataframe_types(self) -> tuple[type, ...]: ...

    @property
    def schema_types(self) -> tuple[type, ...]: ...

    def compile_schema(self, schema: ModelSchema[Any]) -> object: ...

    def coerce_dataframe(
        self,
        dataframe: object,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> object: ...

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> object: ...


_BACKENDS: dict[str, DataFrameBackend] = {}
_BUILTINS_LOADED = False


def register_backend(backend: DataFrameBackend) -> None:
    existing = _BACKENDS.get(backend.name)
    if existing is backend:
        return
    if existing is not None:
        raise ValueError(f"Backend '{backend.name}' is already registered")

    for registered in _BACKENDS.values():
        _raise_for_type_overlap(
            backend,
            registered,
            attribute="dataframe_types",
            kind="dataframe",
        )
        _raise_for_type_overlap(
            backend,
            registered,
            attribute="schema_types",
            kind="schema",
        )
    _BACKENDS[backend.name] = backend


def _raise_for_type_overlap(
    backend: DataFrameBackend,
    registered: DataFrameBackend,
    *,
    attribute: str,
    kind: str,
) -> None:
    candidate_types = getattr(backend, attribute)
    registered_types = getattr(registered, attribute)
    for candidate in candidate_types:
        for registered_type in registered_types:
            if issubclass(candidate, registered_type) or issubclass(
                registered_type, candidate
            ):
                raise TypeError(
                    f"Backend '{backend.name}' has ambiguous {kind} type "
                    f"{candidate!r} with backend '{registered.name}'"
                )


def _load_builtin_backends() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    import_module("data_joinery.backends.spark")
    if find_spec("polars") is not None:
        import_module("data_joinery.backends.polars")


def get_backend(name: str) -> DataFrameBackend:
    if name not in _BACKENDS:
        _load_builtin_backends()
    try:
        return _BACKENDS[name]
    except KeyError as error:
        raise LookupError(
            f"No dataframe backend named '{name}' is registered"
        ) from error


def backend_for_frame_type(frame_type: type) -> DataFrameBackend | None:
    if not isinstance(frame_type, type):
        return None
    backend = _find_backend_for_type(frame_type)
    if backend is not None:
        return backend
    _load_builtin_backends()
    return _find_backend_for_type(frame_type)


def backend_for_schema_type(schema_type: type) -> DataFrameBackend | None:
    if not isinstance(schema_type, type):
        return None
    backend = _find_backend_for_type(schema_type, attribute="schema_types")
    if backend is not None:
        return backend
    _load_builtin_backends()
    return _find_backend_for_type(schema_type, attribute="schema_types")


def _find_backend_for_type(
    frame_type: type,
    *,
    attribute: str = "dataframe_types",
) -> DataFrameBackend | None:
    matches = [
        backend
        for backend in _BACKENDS.values()
        if any(
            issubclass(frame_type, candidate)
            for candidate in getattr(backend, attribute)
        )
    ]
    if len(matches) > 1:
        names = ", ".join(sorted(backend.name for backend in matches))
        raise LookupError(f"Multiple dataframe backends match {frame_type!r}: {names}")
    return matches[0] if matches else None


def backend_for_value(value: object) -> DataFrameBackend | None:
    return backend_for_frame_type(type(value))
