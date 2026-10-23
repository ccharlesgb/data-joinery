from dataclasses import fields
from typing import ClassVar, assert_type

import pytest

from data_joinery.schemas.joinery_model import Column, JoineryModel, column


class User(JoineryModel):
    source: ClassVar[str] = "users"
    id: Column[int]
    name: Column[str]
    account_value: Column[float]
    invalid_column_name: Column[str] = column(name="its got spaces")


class Customer(JoineryModel):
    id: Column[int]
    display_name: Column[str] = column(name="Display Name", default="Unknown")
    tags: Column[list[str]] = column(default_factory=list)
    nickname: Column[str | None] = column(default=None)


class PaidCustomer(Customer):
    account_value: Column[float]


def test_column_names_are_strings():
    assert [User.id, User.name, User.account_value, User.invalid_column_name] == [
        "id",
        "name",
        "account_value",
        "its got spaces",
    ]


def test_instance_values_have_python_types():
    user = User(id=1, name="Ada", account_value=12.5, invalid_column_name="example")

    assert_type(User.id, str)
    assert_type(User.invalid_column_name, str)
    assert_type(user.id, int)
    assert_type(user.account_value, float)
    assert vars(user) == {
        "id": 1,
        "name": "Ada",
        "account_value": 12.5,
        "invalid_column_name": "example",
    }


def test_instance_assignment_does_not_change_the_class():
    customer = Customer(id=1)
    customer.display_name = "Ada"

    assert Customer.display_name == "Display Name"


def test_defaults_and_keyword_only_inheritance():
    actual = PaidCustomer(id=1, account_value=12.5)

    assert vars(actual) == {
        "id": 1,
        "display_name": "Unknown",
        "tags": [],
        "nickname": None,
        "account_value": 12.5,
    }


def test_default_factories_are_independent():
    first = Customer(id=1)
    second = Customer(id=2)
    first.tags.append("new")

    assert second.tags == []


def test_models_have_value_equality():
    assert Customer(id=1) == Customer(id=1)


def test_models_compare_field_values():
    assert Customer(id=1) != Customer(id=2)


def test_models_require_exact_types_for_equality():
    class OtherCustomer(Customer):
        pass

    assert Customer(id=1) != OtherCustomer(id=1)


def test_models_have_dataclass_representations():
    assert repr(Customer(id=1)) == (
        "Customer(id=1, display_name='Unknown', tags=[], nickname=None)"
    )


def test_models_are_unhashable():
    with pytest.raises(TypeError, match="unhashable"):
        hash(Customer(id=1))


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"id": 1, "name": "Ada", "account_value": 12.5},
        {"id": 1, "name": "Ada", "account_value": 12.5, "its got spaces": "x"},
    ],
)
def test_constructor_rejects_missing_or_aliased_arguments(kwargs):
    with pytest.raises(TypeError):
        User(**kwargs)


def test_constructor_rejects_positional_arguments():
    with pytest.raises(TypeError):
        Customer(1)  # type: ignore[bad-argument-count] - exercise runtime checking


def test_classvars_are_not_dataclass_fields():
    assert [item.name for item in fields(User)] == [
        "id",
        "name",
        "account_value",
        "invalid_column_name",
    ]


def test_classvars_keep_their_values():
    assert User.source == "users"


def test_overrides_reset_field_options_and_keep_order():
    class Renamed(Customer):
        display_name: Column[str]

    assert [(item.metadata["column_name"], item.type) for item in fields(Renamed)] == [
        ("id", int),
        ("display_name", str),
        ("tags", list[str]),
        ("nickname", str | None),
    ]


@pytest.mark.parametrize("name", ["", 1])
def test_invalid_column_names_are_rejected(name):
    with pytest.raises(ValueError, match="nonempty column name"):
        type(
            "Invalid",
            (JoineryModel,),
            {
                "__annotations__": {"value": Column[int]},
                "value": column(name=name),
            },
        )


def test_duplicate_aliases_are_rejected():
    with pytest.raises(ValueError, match="duplicate column names"):

        class Duplicate(Customer):
            other: Column[str] = column(name="Display Name")


def test_plain_annotations_are_rejected():
    with pytest.raises(TypeError, match=r"Column\[T\]"):

        class Invalid(JoineryModel):
            value: int


def test_bare_defaults_are_rejected():
    with pytest.raises(TypeError, match="Use column"):
        type(
            "Invalid",
            (JoineryModel,),
            {
                "__annotations__": {"value": Column[int]},
                "value": 1,
            },
        )


def test_conflicting_defaults_are_rejected():
    with pytest.raises(ValueError, match="both default and default_factory"):

        class Invalid(JoineryModel):
            value: Column[int] = column(default=1, default_factory=int)  # type: ignore[bad-class-definition] - exercise runtime checking


def test_mutable_defaults_are_rejected():
    with pytest.raises(ValueError, match="mutable default"):

        class Invalid(JoineryModel):
            value: Column[list[int]] = column(default=[])


def test_reserved_field_names_are_rejected():
    with pytest.raises(ValueError, match="shadows a JoineryModel member"):
        type(
            "Invalid",
            (JoineryModel,),
            {
                "__annotations__": {"__init_subclass__": Column[str]},
            },
        )
