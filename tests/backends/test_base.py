import pytest

from data_joinery.backends import base, protocol, registry


@pytest.mark.parametrize(
    "name",
    [
        "DataFrameBackend",
        "register_backend",
        "get_backend",
        "backend_for_frame_type",
        "backend_for_schema_type",
        "backend_for_value",
    ],
)
def test_legacy_exports_forward_to_canonical_modules(name):
    owner = protocol if name == "DataFrameBackend" else registry

    assert getattr(base, name) is getattr(owner, name)
