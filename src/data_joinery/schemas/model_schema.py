from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, cast

from .joinery_model import JoineryModel

try:
    from pydantic import BaseModel as _PydanticBaseModel
except ModuleNotFoundError as error:
    if error.name != "pydantic":
        raise
    _PydanticBaseModel = None
    _PYDANTIC_AVAILABLE = False
else:
    _PYDANTIC_AVAILABLE = True


def _serialize_dataclass_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            (
                field.metadata["column_name"]
                if is_joinery_model(type(value))
                else field.name
            ): _serialize_dataclass_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple) and hasattr(value, "_fields"):
        return type(value)(*(_serialize_dataclass_value(item) for item in value))
    if isinstance(value, (list, tuple)):
        return type(value)(_serialize_dataclass_value(item) for item in value)
    if isinstance(value, dict):
        return type(value)(
            (_serialize_dataclass_value(key), _serialize_dataclass_value(item))
            for key, item in value.items()
        )
    return deepcopy(value)


@dataclass(frozen=True)
class ModelField:
    name: str
    annotation: Any


@dataclass(frozen=True)
class ModelSchema[T]:
    """Represent a JoineryModel, dataclass, or Pydantic model for DataFrame backends.

    Keep the original model and its field names and Python annotations in a
    common form for compiling native schemas and serializing model instances.

    Attributes:
        model: Original dataclass or Pydantic model class.
        fields: Model fields in declaration order.
    """

    model: type[T]
    fields: tuple[ModelField, ...]

    @classmethod
    def from_model(cls, model: type[T]) -> "ModelSchema[T]":
        """Normalize a model's fields for use by DataFrame backends.

        Read dataclass and Pydantic fields through a common interface so
        backends can compile schemas without handling each model style.

        Args:
            model: Dataclass or Pydantic model class to describe.

        Returns:
            The original model and its fields in declaration order.

        Raises:
            ValueError: If the class is neither a dataclass nor a Pydantic model.
        """
        if not is_schema_model(model):
            raise ValueError(
                f"{model.__name__} is neither a dataclass nor a pydantic model. "
                "Decorate it with @dataclass or use a Pydantic BaseModel."
            )
        return cls(
            model=model,
            fields=tuple(
                ModelField(name, annotation)
                for name, annotation in get_model_fields(model)
            ),
        )

    def serialize_rows(self, rows: Sequence[T]) -> list[dict[str, Any]]:
        """Validate model rows and convert them to Python dictionaries.

        Give DataFrame backends a common row format so they can create frames
        from dataclasses and Pydantic models using the same interface. Check
        that each row matches the schema's model before converting it.

        Args:
            rows: Instances of this schema's model to include in a DataFrame.

        Returns:
            One dictionary per row, in input order. Nested models are converted
            to dictionaries. JoineryModel fields use their column names,
            including inside nested dataclasses and containers.

        Raises:
            ValueError: If a row is not an instance of this schema's model.
        """
        serialized: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, self.model):
                raise ValueError(  # noqa: TRY004
                    f"Row {index}: expected {self.model.__name__}, got "
                    f"{type(row).__name__}. Pass {self.model.__name__} instances."
                )
            if is_dataclass(row) and not isinstance(row, type):
                serialized.append(_serialize_dataclass_value(row))
            else:
                serialized.append(cast(Any, row).model_dump(mode="python"))
        return serialized


def is_joinery_model(klass: Any) -> bool:
    """Check if a class definition is a JoineryModel.

    Args:
        klass: Class to check.

    Returns:
        True if the class inherits from JoineryModel, False otherwise.
    """
    return isinstance(klass, type) and issubclass(klass, JoineryModel)


def is_pydantic_model(klass: Any) -> bool:
    """Check if a class definition is a Pydantic model.

    Uses duck typing to avoid importing Pydantic unless it is installed.

    Args:
        klass: Class to check.

    Returns:
        True if the class is a Pydantic model, False otherwise.
    """
    return (
        _PYDANTIC_AVAILABLE
        and _PydanticBaseModel is not None
        and isinstance(klass, type)
        and issubclass(klass, _PydanticBaseModel)
    )


def is_schema_model(klass: Any) -> bool:
    """Check if a class definition is a dataclass or Pydantic model.

    Args:
        klass: Class to check.

    Returns:
        True if the class is a dataclass or Pydantic model, False otherwise.
    """
    return is_dataclass(klass) or is_pydantic_model(klass)


def get_model_fields(klass: type[Any]) -> list[tuple[str, Any]]:
    """
    Get column names and value types from a schema model.

    Args:
        klass: JoineryModel, dataclass, or Pydantic model class to describe.

    Returns:
        A list of tuples containing the column names and types. JoineryModel
        fields use their configured column names instead of attribute names.

    Raises:
        ValueError: If the class is neither a dataclass nor a Pydantic model.
    """
    if is_joinery_model(klass):
        return [
            (field.metadata["column_name"], field.type)
            for field in fields(cast(Any, klass))
        ]

    if is_dataclass(klass):
        return [(field.name, field.type) for field in fields(klass)]

    if is_pydantic_model(klass):
        model_fields = klass.model_fields
        return [
            (name, field_info.annotation)
            for name, field_info in model_fields.items()
            if field_info.annotation is not None
        ]

    raise ValueError(
        f"{klass.__name__} is neither a dataclass nor a pydantic model. "
        "Decorate it with @dataclass or use a Pydantic BaseModel."
    )
