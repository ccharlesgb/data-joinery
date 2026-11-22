import pytest

from data_joinery.schemas import SchemaCoercionError, SchemaDifference
from data_joinery.schemas.schema_diff import Field, ListElement, SchemaPath


def test_schema_coercion_error_formats_all_violations() -> None:
    error = SchemaCoercionError(
        "project_cast",
        (
            SchemaDifference(
                "missing", (Field("customer"), Field("postcode")), None, "String"
            ),
            SchemaDifference("type_mismatch", (Field("active"),), "Binary", "Boolean"),
        ),
    )

    assert str(error) == (
        "Cannot coerce DataFrame (mode='project_cast'):\n"
        "  - Missing field 'customer.postcode': expected String. "
        "Add the field or update the model.\n"
        "  - Field 'active': expected Boolean, got Binary. "
        "Convert the values to the expected type before coercion."
    )


@pytest.mark.parametrize(
    ("path", "display"),
    [
        ((Field("customer.name"),), '["customer.name"]'),
        ((Field("customer"), Field("name")), "customer.name"),
        ((Field("legacy[]"),), '["legacy[]"]'),
        ((Field("items"), ListElement()), "items[]"),
        (
            (Field("items"), ListElement(), ListElement(), Field("name")),
            "items[][].name",
        ),
        ((Field("customer"), Field("legacy.field")), 'customer["legacy.field"]'),
        ((Field('quote"slash\\'),), '["quote\\"slash\\\\"]'),
        ((Field(""), Field("name")), '[""].name'),
    ],
)
def test_schema_coercion_error_formats_structured_paths(
    path: SchemaPath, display: str
) -> None:
    error = SchemaCoercionError(
        "strict", (SchemaDifference("additional", path, "String", None),)
    )

    assert str(error) == (
        "Cannot coerce DataFrame (mode='strict'):\n"
        f"  - Additional field '{display}': got String. Remove it or add it to the model."
    )
