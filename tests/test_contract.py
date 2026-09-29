from dataclasses import dataclass

import pytest

from data_joinery import Project, Strict
from data_joinery.contract import InstanceContract, VoidContract


@dataclass
class Order:
    order_id: int


@dataclass(frozen=True)
class PathConfig:
    value: str


def test_contract_implementations_determine_compatibility():
    dataframe_contract = Project(Order)
    same_dataframe_contract = Strict(Order)
    value_contract = InstanceContract(PathConfig)

    assert dataframe_contract.accepts(same_dataframe_contract)
    assert not dataframe_contract.accepts(value_contract)
    assert value_contract.accepts(InstanceContract(PathConfig))
    assert not value_contract.accepts(dataframe_contract)


def test_void_contract_accepts_only_void_contract():
    contract = VoidContract()

    assert contract.accepts(VoidContract())
    assert not contract.accepts(InstanceContract(str))


def test_instance_contract_rejects_generic_type():
    with pytest.raises(
        TypeError,
        match=(
            r"InstanceContract requires an unsubscripted runtime class, "
            r"got list\[str\]"
        ),
    ):
        InstanceContract(list[str])  # type: ignore[arg-type]
