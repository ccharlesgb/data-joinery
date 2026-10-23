"""Standalone models with column names on classes and typed values on instances."""

from collections.abc import Callable
from dataclasses import MISSING, dataclass, field, fields
from inspect import get_annotations
from typing import (
    Any,
    ClassVar,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

_MISSING: Any = MISSING


class Column[T]:
    """Return a column name on a class and a Python value on an instance.

    Args:
        name: Column name, or None to use the Python attribute name.
        default: Default instance value when the constructor omits the field.
        default_factory: Callable creating a fresh default for each instance.
    """

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
    """Configure a model field's column name or instance default.

    Args:
        name: Column name, or None to use the Python attribute name.
        default: Default instance value when the constructor omits the field.
        default_factory: Callable creating a fresh default for each instance.
            Cannot be combined with default.

    Returns:
        A column descriptor for a field annotated with Column[T].
    """
    return Column(name=name, default=default, default_factory=default_factory)


@dataclass_transform(kw_only_default=True, field_specifiers=(column,))
class JoineryModel:
    """Define column names and keyword-only, dataclass-like row instances.

    Annotate row fields with Column[T] and constants with ClassVar[T]. Class
    access returns column names; instance access returns the stored values.
    Instances are mutable, have value equality, and do not validate value types
    at runtime. Use column() to configure aliases, defaults, or factories.

    Unlike a normal dataclass, no @dataclass decorator is needed. Constructors
    always use keyword arguments. Field types use Column[T], while instance
    values have type T.

    Examples:
        A normal dataclass stores row values, but a required field has no
        corresponding class attribute:

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class PlainUser:
        ...     id: int
        ...     name: str = "Unknown"
        >>> PlainUser(id=1).id
        1
        >>> hasattr(PlainUser, "id")
        False
        >>> PlainUser.name
        'Unknown'

        A JoineryModel also stores row values. Its class attributes return
        column names, even when the field has an instance default:

        >>> class User(JoineryModel):
        ...     id: Column[int]
        ...     name: Column[str] = column(default="Unknown")
        >>> user = User(id=1)
        >>> user.id, user.name
        (1, 'Unknown')
        >>> User.id, User.name
        ('id', 'name')
        >>> user.name = "Ada"
        >>> user == User(id=1, name="Ada")
        True

        Use name= for a DataFrame column name that differs from the Python
        attribute. Constructor arguments still use the attribute name:

        >>> class Customer(JoineryModel):
        ...     display_name: Column[str] = column(name="Display Name")
        >>> Customer.display_name
        'Display Name'
        >>> Customer(display_name="Ada").display_name
        'Ada'

        Use column(default_factory=...) where a dataclass would use
        field(default_factory=...). Each instance gets its own value:

        >>> class Group(JoineryModel):
        ...     members: Column[list[str]] = column(default_factory=list)
        >>> first, second = Group(), Group()
        >>> first.members.append("Ada")
        >>> second.members
        []
    """

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
            if hasattr(JoineryModel, name):
                raise ValueError(f"Field '{name}' shadows a JoineryModel member.")
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
