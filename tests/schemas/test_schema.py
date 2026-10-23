import pytest

from data_joinery import Schema


def test_schema_rejects_a_non_schema_model():
    class NotASchemaModel:
        pass

    with pytest.raises(
        ValueError,
        match="NotASchemaModel is neither a dataclass nor a pydantic model",
    ):
        Schema(NotASchemaModel)
