# Data Joinery Models

!!! example "Proposed API"

    Not implemented yet. These snippets describe the API and implementation
    approach; they are not runnable documentation examples.

## Define and use a model

``` python
from typing import ClassVar, assert_type

from data_joinery import BaseModel, Column, column


class User(BaseModel):
    source: ClassVar[str] = "users"

    id: Column[int]
    name: Column[str]
    account_value: Column[float]
    invalid_column_name: Column[str] = column(name="its got spaces")


user = User(
    id=1,
    name="Ada",
    account_value=12.50,
    invalid_column_name="example",
)

# Class access returns ordinary column-name strings.
assert User.id == "id"
assert User.name == "name"
assert User.invalid_column_name == "its got spaces"
assert_type(User.id, str)

# Instance access returns typed Python values.
assert user.id == 1
assert user.invalid_column_name == "example"
assert_type(user.id, int)

user.name = "Grace"
assert user.name == "Grace"
assert User.name == "name"

# Actual ClassVars remain constants, outside the schema and constructor.
assert User.source == "users"
```

`name=` changes the DataFrame column name, while constructor arguments always use
Python attribute names. Constructors are keyword-only. Instances have dataclass-like
value equality and `repr`, are mutable and unhashable, and perform no runtime value
validation. Existing dataclass and Pydantic schemas remain supported.

## Implement class and instance access

Use a descriptor with overloaded `__get__` methods. This is the core behavior,
with default-value metadata omitted:

``` python
from typing import cast, overload


class Column[T]:
    def __init__(self, *, name: str | None = None) -> None:
        self.column_name = name

    def __set_name__(self, owner: type[object], name: str) -> None:
        self.attribute_name = name
        if self.column_name is None:
            self.column_name = name

    @overload
    def __get__(self, instance: None, owner: type[object]) -> str: ...

    @overload
    def __get__(
        self, instance: object, owner: type[object] | None = None
    ) -> T: ...

    def __get__(
        self, instance: object | None, owner: type[object] | None = None
    ) -> T | str:
        if instance is None:
            assert self.column_name is not None
            return self.column_name
        return cast(T, instance.__dict__[self.attribute_name])

    def __set__(self, instance: object, value: T) -> None:
        instance.__dict__[self.attribute_name] = value
```

`BaseModel` installs a descriptor even for an annotation without an assigned value,
such as `id: Column[int]`. Descriptors installed after class creation need an
explicit `descriptor.__set_name__(model, attribute_name)` call.

## Generate the constructor

The public typing interface uses
[`dataclass_transform`](https://typing.python.org/en/latest/spec/dataclasses.html).
The following is a **stub**, with function bodies omitted:

``` python
from collections.abc import Callable
from typing import dataclass_transform


def column[T](
    *,
    name: str | None = None,
    default: T = ...,
    default_factory: Callable[[], T] = ...,
) -> Column[T]: ...


@dataclass_transform(kw_only_default=True, field_specifiers=(column,))
class BaseModel: ...
```

At runtime, `column()` returns a descriptor storing its options. An omitted default
needs a private sentinel so that `default=None` remains a real default.

`dataclass_transform` informs type checkers; it does not generate runtime methods.
When a subclass is defined, `BaseModel.__init_subclass__` must collect its fields,
install descriptors, and generate `__init__`, `__repr__`, and `__eq__`.
For `User`, the generated constructor behaves like:

``` python
def __init__(
    self,
    *,
    id: int,
    name: str,
    account_value: float,
    invalid_column_name: str,
) -> None:
    self.id = id
    self.name = name
    self.account_value = account_value
    self.invalid_column_name = invalid_column_name
```

Collect field metadata from declarations rather than `getattr(User, "id")`, which
returns a column-name string. That string must never become a constructor default.
Use `name=` for column aliases: the standardized `alias=` field option would
change the constructor parameter instead.

## Defaults and inheritance

``` python
class Customer(BaseModel):
    id: Column[int]
    display_name: Column[str] = column(name="Display Name", default="Unknown")
    tags: Column[list[str]] = column(default_factory=list)
    nickname: Column[str | None] = column(default=None)


first = Customer(id=1)
second = Customer(id=2)
assert first.display_name == "Unknown"
assert first.nickname is None
assert first.tags is not second.tags


class PaidCustomer(Customer):
    account_value: Column[float]


paid = PaidCustomer(id=3, account_value=10.0)
assert PaidCustomer.display_name == "Display Name"
```

Defaults and factories are mutually exclusive. Mutable defaults require factories.
A nullable type without a default is still required. Inherited fields come first;
overrides keep their position, require compatible value types, and replace field
options. Redeclaring without `name=` resets the column name to the attribute name.

At class definition time, reject empty or duplicate column names, field names
that shadow `BaseModel` members, and row annotations without `Column[T]`.

## Backend types and DataFrames

Use `Annotated` inside `Column[T]` for existing backend overrides:

``` python
from decimal import Decimal
from typing import Annotated

import polars as pl

from data_joinery import Schema


class Balance(BaseModel):
    account_value: Column[
        Annotated[Decimal, pl.Decimal(precision=12, scale=2)]
    ] = column(name="Account Value")


balance = Balance(account_value=Decimal("12.50"))
assert_type(Balance.account_value, str)
assert_type(balance.account_value, Decimal)

schema = Schema(Balance)
frame = schema.create_dataframe([balance], pl.DataFrame)
assert frame.columns == ["Account Value"]
assert schema.native_schema(pl.Schema) == pl.Schema(
    {"Account Value": pl.Decimal(precision=12, scale=2)}
)

selected = frame.select(Balance.account_value)
```

Schema compilation, row serialization, coercion, and transformation contracts use
resolved column names. Coercion does not rename incoming columns or fill missing
columns with instance defaults. Nested models apply aliases within each struct;
class access returns a local column name, not a dotted path. Strings are returned
without backend escaping.

## Type checking requirements

These examples must fail static checking:

``` python
user.id = "wrong"              # Expected int.
User.nmae                     # Unknown field.
User(id=1)                    # Missing required fields.
Customer(1)                   # Keyword-only constructor.
Customer(id="wrong")          # Constructor expects int, not Column[int] or str.
Customer(id=1, unknown=True)   # Unknown constructor argument.
```

Constructor argument errors also raise `TypeError` at runtime; unknown attribute
reads raise `AttributeError`. Wrong value types are only checked statically.

Before release, verify descriptors, constructors, defaults, factories, inheritance,
`ClassVar`, and `Annotated` with Pyrefly, Pyright, and mypy, without user casts or
plugins. Runtime tests must cover instance behavior and alias handling in both
Polars and PySpark.
