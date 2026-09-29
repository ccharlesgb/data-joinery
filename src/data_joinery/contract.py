from dataclasses import dataclass
from typing import Any, Protocol, cast

from .backends import backend_for_frame_type, backend_for_value, get_backend
from .schemas import CoercionMode, Schema


class Contract(Protocol):
    def accepts(self, produced: "Contract") -> bool: ...

    def validate(self, value: object) -> object: ...


class ContractTypeMismatch(TypeError):
    def __init__(self, expected_type: str):
        self.expected_type = expected_type
        super().__init__(f"expected {expected_type}")


@dataclass(frozen=True)
class VoidContract:
    """Contract for transforms that do not produce an output."""

    def accepts(self, produced: Contract) -> bool:
        return isinstance(produced, VoidContract)

    def validate(self, value: object) -> None:
        if value is not None:
            raise ContractTypeMismatch("None")


@dataclass(frozen=True)
class _UncheckedContract:
    def accepts(self, produced: Contract) -> bool:
        return True

    def validate(self, value: object) -> object:
        return value


@dataclass(frozen=True)
class DataFrameContract:
    coercion_mode: CoercionMode
    schema: Schema[Any]
    backend_name: str | None = None
    dataframe_type: type | None = None

    def bind(self, dataframe_type: type) -> "DataFrameContract":
        backend = backend_for_frame_type(dataframe_type)
        if backend is None:
            raise TypeError(
                f"No dataframe backend is registered for annotation {dataframe_type!r}"
            )
        return DataFrameContract(
            coercion_mode=self.coercion_mode,
            schema=self.schema,
            backend_name=backend.name,
            dataframe_type=dataframe_type,
        )

    def accepts(self, produced: Contract) -> bool:
        if not isinstance(produced, DataFrameContract):
            return False
        same_backend = (
            self.backend_name is None
            or produced.backend_name is None
            or self.backend_name == produced.backend_name
        )
        same_dataframe_type = (
            self.dataframe_type is None
            or produced.dataframe_type is None
            or self.dataframe_type is produced.dataframe_type
        )
        return self.schema == produced.schema and same_backend and same_dataframe_type

    def validate(self, value: object) -> object:
        backend = (
            get_backend(self.backend_name)
            if self.backend_name is not None
            else backend_for_value(value)
        )
        expected_types = (
            (self.dataframe_type,)
            if self.dataframe_type is not None
            else backend.dataframe_types
            if backend is not None
            else ()
        )
        if backend is None or not isinstance(value, expected_types):
            expected = (
                self.dataframe_type.__name__
                if self.dataframe_type is not None
                else "registered dataframe"
            )
            raise ContractTypeMismatch(f"a {expected}")
        return backend.coerce_dataframe(
            value, self.schema.model_schema, self.coercion_mode
        )


@dataclass(frozen=True)
class InstanceContract:
    value_type: type

    def __post_init__(self) -> None:
        is_runtime_class = self.value_type is not Any and isinstance(
            self.value_type, type
        )
        if is_runtime_class:
            runtime_type = cast(type, self.value_type)
            try:
                isinstance(None, runtime_type)
                issubclass(runtime_type, runtime_type)
            except TypeError:
                is_runtime_class = False

        if not is_runtime_class:
            raise TypeError(
                "InstanceContract requires an unsubscripted runtime class, "
                f"got {self.value_type!r}. Wrap structured values in a named class "
                "instead."
            )

    def accepts(self, produced: Contract) -> bool:
        return isinstance(produced, InstanceContract) and issubclass(
            produced.value_type, self.value_type
        )

    def validate(self, value: object) -> object:
        if not isinstance(value, self.value_type):
            raise ContractTypeMismatch(f"a {self.value_type.__name__}")
        return value


def ProjectCast(schema: type) -> DataFrameContract:
    return DataFrameContract(coercion_mode="project_cast", schema=Schema(schema))


def ProjectTopLevel(schema: type) -> DataFrameContract:
    return DataFrameContract(coercion_mode="project_top_level", schema=Schema(schema))


def Project(schema: type) -> DataFrameContract:
    return DataFrameContract(coercion_mode="project", schema=Schema(schema))


def Strict(schema: type) -> DataFrameContract:
    return DataFrameContract(coercion_mode="strict", schema=Schema(schema))
