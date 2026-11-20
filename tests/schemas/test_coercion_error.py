from data_joinery.schemas import SchemaCoercionError, SchemaDifference


def test_schema_coercion_error_formats_all_violations() -> None:
    error = SchemaCoercionError(
        "project_cast",
        (
            SchemaDifference("missing", "customer.postcode", None, "String"),
            SchemaDifference("type_mismatch", "active", "Binary", "Boolean"),
        ),
    )

    assert str(error) == (
        "Cannot coerce DataFrame (mode='project_cast'):\n"
        "  - Missing field 'customer.postcode': expected String. "
        "Add the field or update the model.\n"
        "  - Field 'active': expected Boolean, got Binary. "
        "Convert the values to the expected type before coercion."
    )
