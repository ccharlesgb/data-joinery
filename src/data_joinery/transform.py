import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import (
    Annotated,
    Any,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from .backends import backend_for_frame_type
from .contract import (
    Contract,
    ContractTypeMismatch,
    DataFrameContract,
    InstanceContract,
    VoidContract,
    _UncheckedContract,
)
from .dependencies import Context
from .utils import get_callable_name


def _get_annotated_dataframe_schema(annotation: Any) -> DataFrameContract | None:
    if get_origin(annotation) is not Annotated:
        return None

    annotated_args = get_args(annotation)
    if len(annotated_args) < 2:
        return None

    base_type = annotated_args[0]
    metadata = annotated_args[1:]
    for metadata_value in metadata:
        if isinstance(metadata_value, DataFrameContract):
            return metadata_value.bind(base_type)

    return None


def _is_annotated_dataframe(annotation: Any) -> bool:
    if get_origin(annotation) is not Annotated:
        return False
    base_type = get_args(annotation)[0]
    return isinstance(base_type, type) and backend_for_frame_type(base_type) is not None


def _get_context_marker(annotation: Any) -> tuple[type, Context] | None:
    if get_origin(annotation) is not Annotated:
        return None

    annotated_args = get_args(annotation)
    if len(annotated_args) < 2:
        return None

    base_type = annotated_args[0]
    metadata = annotated_args[1:]
    for metadata_value in metadata:
        if isinstance(metadata_value, Context):
            return base_type, metadata_value

    return None


@dataclass(frozen=True)
class TransformSpec:
    input_contracts: dict[str, Contract]
    output_contract: Contract
    context_parameters: dict[str, tuple[type, Context]]


def _inspect_transform(f: Any) -> TransformSpec:
    signature = inspect.signature(f)
    type_hints = get_type_hints(f, include_extras=True)
    input_schemas: dict[str, Contract] = {}
    context_parameters: dict[str, tuple[type, Context]] = {}

    for parameter_name in signature.parameters:
        parameter_type = type_hints.get(parameter_name)
        if parameter_type is None:
            continue

        dataframe_schema = _get_annotated_dataframe_schema(parameter_type)
        if dataframe_schema is not None:
            input_schemas[parameter_name] = dataframe_schema
            continue

        context_marker = _get_context_marker(parameter_type)
        if context_marker is not None:
            context_parameters[parameter_name] = context_marker
            continue

        if not _is_annotated_dataframe(parameter_type):
            input_schemas[parameter_name] = InstanceContract(parameter_type)

    output_contract: Contract = VoidContract()
    return_type = type_hints.get("return")
    if return_type is not None and return_type is not type(None):
        dataframe_schema = _get_annotated_dataframe_schema(return_type)
        if dataframe_schema is not None:
            output_contract = dataframe_schema
        elif _is_annotated_dataframe(return_type):
            output_contract = _UncheckedContract()
        else:
            output_contract = InstanceContract(return_type)

    return TransformSpec(
        input_contracts=input_schemas,
        output_contract=output_contract,
        context_parameters=context_parameters,
    )


def _wrap_transform[**P, R](
    fn: Callable[P, R],
    spec: TransformSpec,
) -> Callable[P, R]:
    signature = inspect.signature(fn)

    @wraps(fn)
    def wrapper(*args: P.args, **kwds: P.kwargs) -> R:
        bound_arguments = signature.bind(*args, **kwds)
        bound_arguments.apply_defaults()

        for parameter_name, expected_contract in spec.input_contracts.items():
            value = bound_arguments.arguments.get(parameter_name)
            try:
                bound_arguments.arguments[parameter_name] = expected_contract.validate(
                    value
                )
            except ContractTypeMismatch as e:
                raise TypeError(
                    f"Parameter '{parameter_name}' must be {e.expected_type}"
                ) from None
            except ValueError as e:
                raise ValueError(
                    f"Schema mismatch for parameter '{parameter_name}'"
                ) from e

        result = fn(*bound_arguments.args, **bound_arguments.kwargs)

        try:
            result = cast(R, spec.output_contract.validate(result))
        except ContractTypeMismatch as e:
            raise TypeError(
                f"Return value from '{fn.__name__}' must be {e.expected_type}"
            ) from None
        except ValueError as e:
            raise ValueError(f"Return schema mismatch for '{fn.__name__}'") from e

        return result

    return wrapper


class Transform[**P, R]:
    def __init__(self, fn: Callable[P, R]):
        self._fn = fn
        self.__transform_spec__ = _inspect_transform(fn)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> R:
        return _wrap_transform(self._fn, self.__transform_spec__)(*args, **kwds)

    def get_signature(self) -> inspect.Signature:
        return inspect.signature(self._fn)

    @property
    def default_name(self) -> str | None:
        return get_callable_name(self._fn)


@overload
def transform[**P, R](
    f: Callable[P, R],
) -> Transform[P, R]: ...


@overload
def transform[**P, R](
    f: None = None,
) -> Callable[[Callable[P, R]], Transform[P, R]]: ...


def transform[**P, R](
    f: Callable[P, R] | None = None,
) -> Transform[P, R] | Callable[[Callable[P, R]], Transform[P, R]]:
    if f is None:
        return Transform

    return Transform(f)
