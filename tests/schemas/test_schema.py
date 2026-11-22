import pytest

from data_joinery import Column, JoineryModel, Schema, column
from data_joinery.schemas import CoercionMode, DifferenceKind, SchemaCoercionError
from data_joinery.schemas.schema_diff import Field, ListElement, SchemaPath
from tests.conftest import BackendHelper
from tests.models import Item


def test_schema_rejects_a_non_schema_model() -> None:
    class NotASchemaModel:
        pass

    with pytest.raises(
        ValueError,
        match="NotASchemaModel is neither a dataclass nor a pydantic model",
    ):
        Schema(NotASchemaModel)


def test_create_dataframe_serializes_model_rows[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class Row(JoineryModel):
        row_id: Column[int] = column(name="id")
        item: Column[Item]
        items: Column[list[Item]]

    schema = Schema(Row)
    expected = dataframe_backend.from_records(
        [
            {"id": 1, "item": {"value": 2}, "items": [{"value": 3}, {"value": 4}]},
            {"id": 5, "item": {"value": 6}, "items": []},
        ],
        schema,
    )

    actual = dataframe_backend.create(
        schema,
        Row(row_id=1, item=Item(value=2), items=[Item(value=3), Item(value=4)]),
        Row(row_id=5, item=Item(value=6), items=[]),
    )

    dataframe_backend.assert_equal(actual, expected)


def test_create_dataframe_rejects_rows_of_a_different_type[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class OtherItem(JoineryModel):
        value: Column[int]

    with pytest.raises(ValueError, match="Row 1: expected Item, got OtherItem"):
        dataframe_backend.create(Schema(Item), Item(value=1), OtherItem(value=2))  # type: ignore[bad-argument-type]


def test_create_dataframe_rejects_unknown_options[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    with pytest.raises(TypeError, match="unexpected_option"):
        Schema(Item).create_dataframe(
            [Item(value=1)],
            dataframe_backend.frame_type,
            **dataframe_backend.create_options,
            unexpected_option=True,
        )


def test_strict_preserves_values_and_input_column_order[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class Row(JoineryModel):
        first: Column[int]
        second: Column[str]

    class ReorderedRow(JoineryModel):
        second: Column[str]
        first: Column[int]

    source = dataframe_backend.create(
        Schema(ReorderedRow), ReorderedRow(second="a", first=1)
    )

    actual = Schema(Row).coerce_dataframe(source, "strict")

    dataframe_backend.assert_equal(actual, source)


def test_default_coercion_rejects_extra_columns[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class ItemWithLegacyField(Item):
        legacy: Column[int]

    source = dataframe_backend.create(
        Schema(ItemWithLegacyField), ItemWithLegacyField(value=1, legacy=2)
    )

    with pytest.raises(SchemaCoercionError, match="Additional field 'legacy'"):
        Schema(Item).coerce_dataframe(source)


_MISSING_FIELDS = [
    ("missing", (Field("customer"), Field("postcode"))),
    ("missing", (Field("required"),)),
]
_TYPE_MISMATCHES = [
    ("type_mismatch", (Field("customer"), Field("name"))),
    ("type_mismatch", (Field("items"), ListElement())),
]
_NESTED_EXTRA = [("additional", (Field("customer"), Field("legacy")))]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            "strict",
            [
                *_MISSING_FIELDS,
                ("additional", (Field("extra"),)),
                *_NESTED_EXTRA,
                *_TYPE_MISMATCHES,
            ],
        ),
        ("project_top_level", [*_MISSING_FIELDS, *_NESTED_EXTRA, *_TYPE_MISMATCHES]),
        ("project", [*_MISSING_FIELDS, *_TYPE_MISMATCHES]),
        ("project_cast", _MISSING_FIELDS),
    ],
)
def test_coercion_reports_all_schema_violations[FrameT](
    dataframe_backend: BackendHelper[FrameT],
    mode: CoercionMode,
    expected: list[tuple[DifferenceKind, SchemaPath]],
) -> None:
    class SourceCustomer(JoineryModel):
        name: Column[int]
        legacy: Column[str]

    class TargetCustomer(JoineryModel):
        name: Column[str]
        postcode: Column[str]

    class SourceRow(JoineryModel):
        extra: Column[str]
        customer: Column[SourceCustomer]
        items: Column[list[int]]

    class TargetRow(JoineryModel):
        customer: Column[TargetCustomer]
        items: Column[list[str]]
        required: Column[int]

    source = dataframe_backend.create(
        Schema(SourceRow),
        SourceRow(
            extra="drop", customer=SourceCustomer(name=1, legacy="old"), items=[2]
        ),
    )

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(TargetRow).coerce_dataframe(source, mode)

    assert [(item.kind, item.path) for item in caught.value.violations] == expected


@pytest.mark.parametrize("column_name", ["legacy.field", "legacy[]", "[]"])
def test_project_top_level_drops_extra_columns_with_path_markers[FrameT](
    dataframe_backend: BackendHelper[FrameT], column_name: str
) -> None:
    class ItemWithLegacyField(Item):
        legacy: Column[int] = column(name=column_name)

    source = dataframe_backend.create(
        Schema(ItemWithLegacyField), ItemWithLegacyField(value=1, legacy=2)
    )

    schema = Schema(Item)
    expected = dataframe_backend.create(schema, Item(value=1))

    actual = schema.coerce_dataframe(source, "project_top_level")

    dataframe_backend.assert_equal(actual, expected)


@pytest.mark.parametrize("column_name", ["legacy.field", "legacy[]", "[]"])
def test_project_top_level_rejects_nested_extra_fields_with_path_markers[FrameT](
    dataframe_backend: BackendHelper[FrameT], column_name: str
) -> None:
    class ItemWithLegacyField(Item):
        legacy: Column[int] = column(name=column_name)

    class SourceRow(JoineryModel):
        items: Column[list[list[ItemWithLegacyField]]] = column(name="items[]")

    class TargetRow(JoineryModel):
        items: Column[list[list[Item]]] = column(name="items[]")

    source = dataframe_backend.create(
        Schema(SourceRow), SourceRow(items=[[ItemWithLegacyField(value=1, legacy=2)]])
    )
    expected = [
        (
            "additional",
            (Field("items[]"), ListElement(), ListElement(), Field(column_name)),
        )
    ]

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(TargetRow).coerce_dataframe(source, "project_top_level")

    assert [(item.kind, item.path) for item in caught.value.violations] == expected


@pytest.mark.parametrize("column_name", ["*", "^.*$", "customer.name", "a`b"])
@pytest.mark.parametrize("mode", ["project_top_level", "project", "project_cast"])
def test_projection_preserves_literal_column_names[FrameT](
    dataframe_backend: BackendHelper[FrameT],
    column_name: str,
    mode: CoercionMode,
) -> None:
    class Customer(JoineryModel):
        name: Column[str]

    class SourceRow(JoineryModel):
        legacy: Column[int] = column(name="legacy.field")
        customer: Column[Customer]
        literal: Column[str] = column(name=column_name)

    class TargetRow(JoineryModel):
        literal: Column[str] = column(name=column_name)
        customer: Column[Customer]

    customer = Customer(name="nested")
    source = dataframe_backend.create(
        Schema(SourceRow), SourceRow(legacy=99, customer=customer, literal="literal")
    )
    schema = Schema(TargetRow)
    expected = dataframe_backend.create(
        schema, TargetRow(literal="literal", customer=customer)
    )

    actual = schema.coerce_dataframe(source, mode)

    dataframe_backend.assert_equal(actual, expected)


@pytest.mark.parametrize("column_name", ["*", "customer.name", "a`b"])
def test_strict_preserves_literal_column_names[FrameT](
    dataframe_backend: BackendHelper[FrameT], column_name: str
) -> None:
    class Customer(JoineryModel):
        name: Column[str]

    class TargetRow(JoineryModel):
        literal: Column[str] = column(name=column_name)
        customer: Column[Customer]

    schema = Schema(TargetRow)
    expected = dataframe_backend.create(
        schema, TargetRow(literal="literal", customer=Customer(name="nested"))
    )

    actual = schema.coerce_dataframe(expected, "strict")

    dataframe_backend.assert_equal(actual, expected)


def test_project_top_level_selects_model_columns_in_order[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class SourceRow(JoineryModel):
        extra: Column[str]
        item: Column[Item]
        row_id: Column[int]

    class ProjectedRow(JoineryModel):
        row_id: Column[int]
        item: Column[Item]

    item = Item(value=2)
    source = dataframe_backend.create(
        Schema(SourceRow), SourceRow(extra="drop", item=item, row_id=1)
    )
    schema = Schema(ProjectedRow)
    expected = dataframe_backend.create(schema, ProjectedRow(row_id=1, item=item))

    actual = schema.coerce_dataframe(source, "project_top_level")

    dataframe_backend.assert_equal(actual, expected)


@pytest.mark.parametrize("mode", ["project", "project_cast"])
def test_recursive_projection_preserves_values_and_null_structs[FrameT](
    dataframe_backend: BackendHelper[FrameT], mode: CoercionMode
) -> None:
    class ProjectedItem(JoineryModel):
        value: Column[int | None]

    class SourceItem(ProjectedItem):
        extra: Column[int]

    class SourceRow(JoineryModel):
        nested: Column[SourceItem | None]
        items: Column[list[SourceItem | None]]
        extra: Column[str]

    class ProjectedRow(JoineryModel):
        nested: Column[ProjectedItem | None]
        items: Column[list[ProjectedItem | None]]

    source_null = SourceItem(value=None, extra=1)
    source_value = SourceItem(value=2, extra=3)
    source = dataframe_backend.create(
        Schema(SourceRow),
        SourceRow(nested=None, items=[None, source_null, source_value], extra="drop"),
        SourceRow(nested=source_null, items=[], extra="drop"),
        SourceRow(nested=source_value, items=[], extra="drop"),
    )
    schema = Schema(ProjectedRow)
    expected = dataframe_backend.create(
        schema,
        ProjectedRow(
            nested=None, items=[None, ProjectedItem(value=None), ProjectedItem(value=2)]
        ),
        ProjectedRow(nested=ProjectedItem(value=None), items=[]),
        ProjectedRow(nested=ProjectedItem(value=2), items=[]),
    )

    actual = schema.coerce_dataframe(source, mode)

    dataframe_backend.assert_equal(actual, expected)


def test_project_cast_casts_top_level_and_nested_values[FrameT](
    dataframe_backend: BackendHelper[FrameT],
) -> None:
    class TextItem(JoineryModel):
        value: Column[str]
        extra: Column[int]

    class SourceRow(JoineryModel):
        row_id: Column[float]
        item: Column[TextItem]
        items: Column[list[TextItem]]

    class ProjectedRow(JoineryModel):
        row_id: Column[int]
        item: Column[Item]
        items: Column[list[Item]]

    source = dataframe_backend.create(
        Schema(SourceRow),
        SourceRow(
            row_id=1.9,
            item=TextItem(value="2", extra=3),
            items=[TextItem(value="4", extra=5), TextItem(value="6", extra=7)],
        ),
    )
    schema = Schema(ProjectedRow)
    expected = dataframe_backend.create(
        schema,
        ProjectedRow(
            row_id=1, item=Item(value=2), items=[Item(value=4), Item(value=6)]
        ),
    )

    actual = schema.coerce_dataframe(source, "project_cast")

    dataframe_backend.assert_equal(actual, expected)
