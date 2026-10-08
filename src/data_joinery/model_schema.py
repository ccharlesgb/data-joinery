from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, TypeVar

try:
    from pydantic import BaseModel as _PydanticBaseModel
except ModuleNotFoundError as error:
    if error.name != "pydantic":
        raise
    _PydanticBaseModel = None
    _PYDANTIC_AVAILABLE = False
else:
    _PYDANTIC_AVAILABLE = True


T = TypeVar("T")


@dataclass(frozen=True)
class ModelField:
    name: str
    annotation: Any


@dataclass(frozen=True)
class ModelSchema[T]:
    model: type[T]
    fields: tuple[ModelField, ...]

    @classmethod
    def from_model(cls, model: type[T]) -> "ModelSchema[T]":
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

    def serialize_rows(self, rows: Sequence[T]) -> list[object]:
        serialized: list[object] = []
        for index, row in enumerate(rows):
            if not isinstance(row, self.model):
                raise ValueError(  # noqa: TRY004
                    f"Row {index}: expected {self.model.__name__}, got "
                    f"{type(row).__name__}. Pass {self.model.__name__} instances."
                )
            model_dump = getattr(row, "model_dump", None)
            serialized.append(
                model_dump(mode="python") if callable(model_dump) else row
            )
        return serialized


def is_pydantic_model(klass: Any) -> bool:
    return (
        _PYDANTIC_AVAILABLE
        and _PydanticBaseModel is not None
        and isinstance(klass, type)
        and issubclass(klass, _PydanticBaseModel)
    )


def is_schema_model(klass: Any) -> bool:
    return is_dataclass(klass) or is_pydantic_model(klass)


def get_model_fields(klass: type[Any]) -> list[tuple[str, Any]]:
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
