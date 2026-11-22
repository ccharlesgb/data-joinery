from data_joinery.schemas.coercion import find_coercion_violations
from data_joinery.schemas.schema_diff import Field, SchemaDiff, SchemaDifference


def test_find_coercion_violations_returns_differences_without_raising() -> None:
    missing = SchemaDifference("missing", (Field("name"),), None, "String")
    additional = SchemaDifference("additional", (Field("legacy"),), "String", None)
    mismatch = SchemaDifference(
        "type_mismatch", (Field("active"),), "Binary", "Boolean"
    )
    diff = SchemaDiff(
        additional=(additional,),
        missing=(missing,),
        type_mismatches=(mismatch,),
    )
    expected = (missing, additional, mismatch)

    actual = find_coercion_violations(diff, "strict", lambda given, target: False)

    assert actual == expected


def test_find_coercion_violations_returns_empty_when_differences_are_permitted() -> (
    None
):
    diff = SchemaDiff(
        additional=(
            SchemaDifference("additional", (Field("legacy"),), "String", None),
        ),
        missing=(),
        type_mismatches=(
            SchemaDifference("type_mismatch", (Field("value"),), "Int32", "Int64"),
        ),
    )

    actual = find_coercion_violations(diff, "project_cast", lambda given, target: True)

    assert actual == ()
