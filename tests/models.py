from dataclasses import dataclass
from datetime import date

from data_joinery import Column, JoineryModel, column


class Department(JoineryModel):
    """A department identified by its numeric ID."""

    department_id: Column[int]


class Item(JoineryModel):
    """An item with an integer value."""

    value: Column[int]


class JoineryDetail(JoineryModel):
    """A nested model with an aliased date column."""

    day: Column[date] = column(name="Event Day")


class Order(JoineryModel):
    """An order identified by its numeric ID."""

    order_id: Column[int]


@dataclass(frozen=True)
class PathConfig:
    """A path provided as a context dependency."""

    value: str


class Row(JoineryModel):
    """A dataframe row with an integer value."""

    value: Column[int]
