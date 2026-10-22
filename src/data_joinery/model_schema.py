from collections.abc import Callable, Sequence
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from inspect import get_annotations
from typing import (
    Any,
    ClassVar,
    TypeVar,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

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
_MISSING: Any = MISSING


class Column[T]:
    """Return a column name on a class and a Python value on an instance."""

    def __init__(
        self,
        *,
        name: str | None = None,
        default: Any = MISSING,
        default_factory: Any = MISSING,
    ) -> None:
        self.column_name = name
        self.default = default
        self.default_factory = default_factory

    def __set_name__(self, owner: type[object], name: str) -> None:
        self.attribute_name = name
        if self.column_name is None:
            self.column_name = name

    @overload
    def __get__(self, instance: None, owner: type[object]) -> str: ...

    @overload
    def __get__(self, instance: object, owner: type[object] | None = None) -> T: ...

    def __get__(
        self, instance: object | None, owner: type[object] | None = None
    ) -> T | str:
        if instance is None:
            assert self.column_name is not None
            return self.column_name
        return cast(T, instance.__dict__[self.attribute_name])

    def __set__(self, instance: object, value: T) -> None:
        instance.__dict__[self.attribute_name] = value


def column[T](
    *,
    name: str | None = None,
    default: T = _MISSING,
    default_factory: Callable[[], T] = _MISSING,
) -> Column[T]:
    """Configure a model field's column name or instance default."""
    return Column(name=name, default=default, default_factory=default_factory)


@dataclass_transform(kw_only_default=True, field_specifiers=(column,))
class BaseModel:
    """Experimental schema model with keyword-only, dataclass-like instances."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        annotations = get_annotations(cls)
        resolved = get_type_hints(cls, localns={cls.__name__: cls}, include_extras=True)
        value_annotations = dict(annotations)
        descriptors: dict[str, Column[Any]] = {}

        for name in annotations:
            annotation = resolved[name]
            if get_origin(annotation) is ClassVar:
                continue
            if get_origin(annotation) is not Column:
                raise TypeError(
                    f"{cls.__name__}.{name} must be annotated with Column[T]."
                )
            if hasattr(BaseModel, name):
                raise ValueError(f"Field '{name}' shadows a BaseModel member.")
            descriptor = cls.__dict__.get(name, Column())
            if not isinstance(descriptor, Column):
                raise TypeError(f"Use column(default=...) for field '{name}'.")
            # An explicitly assigned descriptor has already received __set_name__.
            descriptor.__set_name__(cls, name)
            column_name = descriptor.column_name
            if not isinstance(column_name, str) or not column_name:
                raise ValueError(f"Field '{name}' needs a nonempty column name.")
            value_annotations[name] = get_args(annotation)[0]
            descriptors[name] = descriptor
            setattr(
                cls,
                name,
                field(
                    default=descriptor.default,
                    default_factory=descriptor.default_factory,
                    metadata={"column_name": column_name},
                ),
            )

        # Generate methods before installing descriptors, so column names cannot
        # accidentally become constructor defaults. Keep Python value annotations.
        cls.__annotations__ = value_annotations
        model = dataclass(cls, kw_only=True)
        column_names = [f.metadata["column_name"] for f in fields(cast(Any, model))]
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"{cls.__name__} has duplicate column names.")
        for name, descriptor in descriptors.items():
            setattr(cls, name, descriptor)


def _serialize_model_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            f.metadata.get("column_name", f.name): _serialize_model_value(
                getattr(value, f.name)
            )
            for f in fields(value)
        }
    if isinstance(value, list):
        return [_serialize_model_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_serialize_model_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _serialize_model_value(item) for key, item in value.items()}
    return value


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
            if isinstance(row, BaseModel):
                serialized.append(_serialize_model_value(row))
            else:
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
    if isinstance(klass, type) and issubclass(klass, BaseModel):
        return [(f.metadata["column_name"], f.type) for f in fields(cast(Any, klass))]

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
