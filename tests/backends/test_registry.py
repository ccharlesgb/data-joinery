import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

import pytest

from data_joinery import Project, Schema, Strict, transform
from data_joinery.backends import (
    DataFrameBackend,
    backend_for_frame_type,
    backend_for_schema_type,
    register_backend,
)
from data_joinery.schemas.coercion import CoercionMode
from data_joinery.schemas.model_schema import ModelSchema


@dataclass(frozen=True)
class FakeDataFrame:
    columns: tuple[str, ...]


@dataclass(frozen=True)
class OtherFakeDataFrame:
    columns: tuple[str, ...]


class FakeBackend(
    DataFrameBackend[FakeDataFrame | OtherFakeDataFrame, tuple[str, ...]]
):
    name = "fake"
    dataframe_types = (FakeDataFrame, OtherFakeDataFrame)
    schema_type = tuple

    def compile_schema(self, schema: ModelSchema[Any]) -> tuple[str, ...]:
        return tuple(field.name for field in schema.fields)

    def coerce_dataframe(
        self,
        dataframe: FakeDataFrame | OtherFakeDataFrame,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> FakeDataFrame | OtherFakeDataFrame:
        if not isinstance(dataframe, self.dataframe_types):
            raise TypeError
        expected = tuple(field.name for field in schema.fields)
        if mode == "strict" and set(dataframe.columns) != set(expected):
            raise ValueError("schema mismatch")
        return type(dataframe)(expected)

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        frame_type: type[FakeDataFrame | OtherFakeDataFrame],
        **kwargs: object,
    ) -> FakeDataFrame | OtherFakeDataFrame:
        if kwargs:
            raise TypeError
        schema.serialize_rows(rows)
        return frame_type(tuple(field.name for field in schema.fields))


FAKE_BACKEND = FakeBackend()
register_backend(FAKE_BACKEND)


@dataclass
class Order:
    order_id: int


def test_schema_compiles_with_a_registered_backend():
    schema = Schema(Order)

    assert schema.native_schema(tuple) == ("order_id",)


def test_schema_creates_a_registered_dataframe_type():
    schema = Schema(Order)

    assert schema.create_dataframe([Order(1)], FakeDataFrame) == FakeDataFrame(
        ("order_id",)
    )


def test_backend_is_discovered_from_its_native_schema_type():
    assert backend_for_schema_type(tuple) is FAKE_BACKEND


def test_backend_is_discovered_from_its_second_dataframe_type():
    assert backend_for_frame_type(OtherFakeDataFrame) is FAKE_BACKEND


def test_schema_creates_the_requested_second_dataframe_type():
    expected = OtherFakeDataFrame(("order_id",))

    assert Schema(Order).create_dataframe([Order(1)], OtherFakeDataFrame) == expected


def test_unbound_contract_accepts_the_second_dataframe_type():
    expected = OtherFakeDataFrame(("order_id",))

    assert (
        Project(Order).validate(OtherFakeDataFrame(("extra", "order_id"))) == expected
    )


def test_backend_matches_subclasses_of_its_registered_types():
    class SpecializedFrame(FakeDataFrame):
        pass

    assert backend_for_frame_type(SpecializedFrame) is FAKE_BACKEND


def test_backend_matches_subclasses_of_its_registered_schema_type():
    class SpecializedSchema(tuple):
        pass

    assert backend_for_schema_type(SpecializedSchema) is FAKE_BACKEND


def test_registration_rejects_an_ambiguous_dataframe_type():
    class OtherSchema:
        pass

    class AmbiguousBackend(FakeBackend):
        name = "ambiguous-frame"
        schema_type = OtherSchema  # type: ignore[bad-assignment] - test a different type

    with pytest.raises(TypeError, match="ambiguous dataframe type"):
        register_backend(AmbiguousBackend())


def test_registration_rejects_an_ambiguous_second_dataframe_type():
    class OtherSchema:
        pass

    class NewDataFrame:
        pass

    class AmbiguousBackend(FakeBackend):
        name = "ambiguous-second-frame"
        dataframe_types = (NewDataFrame, OtherFakeDataFrame)  # type: ignore[bad-assignment]
        schema_type = OtherSchema  # type: ignore[bad-assignment]

    with pytest.raises(TypeError, match="ambiguous dataframe type"):
        register_backend(AmbiguousBackend())


def test_registration_rejects_an_ambiguous_schema_type():
    class OtherDataFrame:
        pass

    class AmbiguousBackend(FakeBackend):
        name = "ambiguous-schema"
        dataframe_types = (OtherDataFrame,)  # type: ignore[bad-assignment] - test a different type

    with pytest.raises(TypeError, match="ambiguous schema type"):
        register_backend(AmbiguousBackend())


def test_transform_binds_dataframe_contract_to_annotation_backend():
    @transform
    def select_order(
        frame: Annotated[FakeDataFrame, Project(Order)],
    ) -> Annotated[FakeDataFrame, Strict(Order)]:
        return frame

    contract = select_order.__transform_spec__.input_contracts["frame"]

    assert contract.backend_name == "fake"  # type: ignore[attr-defined]


def test_transform_coerces_with_a_registered_backend():
    @transform
    def select_order(
        frame: Annotated[FakeDataFrame, Project(Order)],
    ) -> Annotated[FakeDataFrame, Strict(Order)]:
        return frame

    assert select_order(FakeDataFrame(("extra", "order_id"))) == FakeDataFrame(
        ("order_id",)
    )


@pytest.mark.parametrize(
    "lookup",
    [
        "get_backend('standalone')",
        "backend_for_frame_type(Frame)",
        "backend_for_schema_type(NativeSchema)",
        "backend_for_value(Frame())",
    ],
)
def test_custom_registration_in_fresh_interpreter_without_optional_imports(lookup):
    script = """
import sys

class BlockOptionalImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pyspark', 'polars'}:
            raise AssertionError(f'Unexpected optional import: {fullname}')

sys.meta_path.insert(0, BlockOptionalImports())
from data_joinery.backends import (
    DataFrameBackend, register_backend, get_backend,
    backend_for_frame_type, backend_for_schema_type, backend_for_value,
)

class Frame:
    pass

class NativeSchema:
    pass

class Backend:
    name = 'standalone'
    dataframe_types = (Frame,)
    schema_type = NativeSchema

backend = Backend()
register_backend(backend)
register_backend(backend)
"""
    subprocess.run(
        [sys.executable, "-c", script + f"\nassert {lookup} is backend\n"],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("name", ["polars", "spark"])
@pytest.mark.parametrize("entrypoint", ["registry", "package", "backend", "types"])
def test_builtin_discovery_in_fresh_interpreter(name, entrypoint):
    pytest.importorskip("pyspark" if name == "spark" else name)

    module_name = f"data_joinery.backends.{name}"
    if entrypoint in {"backend", "types"}:
        module_name += f".{entrypoint}"
    script = f"""
import sys
from importlib import import_module
from data_joinery.backends import get_backend

assert 'data_joinery.backends.polars' not in sys.modules
assert 'data_joinery.backends.spark' not in sys.modules
assert 'polars' not in sys.modules
assert 'pyspark' not in sys.modules
if {entrypoint!r} != 'registry':
    import_module({module_name!r})
backend = get_backend({name!r})
assert backend.name == {name!r}
package = import_module('data_joinery.backends.' + {name!r})
implementation = import_module(package.__name__ + '.backend')
instance_name = {name!r}.upper() + '_BACKEND'
assert backend is getattr(package, instance_name)
assert backend is getattr(implementation, instance_name)
from data_joinery.backends.registry import backend_for_frame_type, backend_for_schema_type
for frame_type in backend.dataframe_types:
    assert backend_for_frame_type(frame_type) is backend
assert backend_for_schema_type(backend.schema_type) is backend
"""
    subprocess.run(
        [sys.executable, "-c", script], check=True, capture_output=True, text=True
    )
