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

from .context import Context
from .contract import (
    Contract,
    ContractTypeMismatch,
    DataFrameContract,
    InstanceContract,
    VoidContract,
)
from .schemas.coercion_error import SchemaCoercionError
from .utils import get_callable_name


def _parse_annotation(
    annotation: Any, location: str
) -> tuple[Any, DataFrameContract | Context | None]:
    if get_origin(annotation) is not Annotated:
        return annotation, None

    base_type, *metadata = get_args(annotation)
    markers = [
        value for value in metadata if isinstance(value, (DataFrameContract, Context))
    ]
    if len(markers) > 1:
        raise TypeError(
            f"{location}: only one DataFrame contract or Context() marker is allowed."
        )
    return base_type, next(iter(markers), None)


def _make_contract(
    base_type: type, marker: DataFrameContract | None, location: str
) -> Contract:
    try:
        if marker is not None:
            return marker.bind(base_type)
        return InstanceContract(base_type)
    except TypeError as error:
        raise TypeError(f"{location}: {error}") from None


@dataclass(frozen=True)
class TransformSpec:
    input_contracts: dict[str, Contract]
    output_contract: Contract
    context_parameters: dict[str, tuple[type, Context]]


def _inspect_transform(f: Any) -> TransformSpec:
    signature = inspect.signature(f)
    type_hints = get_type_hints(f, include_extras=True)
    input_contracts: dict[str, Contract] = {}
    context_parameters: dict[str, tuple[type, Context]] = {}
    transform_name = get_callable_name(f) or "<lambda>"

    for parameter_name in signature.parameters:
        if parameter_name not in type_hints:
            continue

        location = f"Transform '{transform_name}' parameter '{parameter_name}'"
        parameter_type, marker = _parse_annotation(type_hints[parameter_name], location)
        if isinstance(marker, Context):
            context_parameters[parameter_name] = (parameter_type, marker)
        else:
            input_contracts[parameter_name] = _make_contract(
                parameter_type, marker, location
            )

    location = f"Transform '{transform_name}' return annotation"
    return_type, marker = _parse_annotation(
        type_hints.get("return", type(None)), location
    )
    if isinstance(marker, Context):
        raise TypeError(f"{location}: Context() can only mark a parameter.")

    output_contract: Contract
    if return_type is type(None) and marker is None:
        output_contract = VoidContract()
    else:
        output_contract = _make_contract(return_type, marker, location)

    return TransformSpec(
        input_contracts=input_contracts,
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
                    f"Transform '{fn.__name__}' parameter '{parameter_name}' must be "
                    f"{e.expected_type}; got {type(value).__name__}."
                ) from None
            except SchemaCoercionError as e:
                raise SchemaCoercionError(
                    e.mode,
                    e.violations,
                    location=(
                        f"Transform '{fn.__name__}' parameter '{parameter_name}'"
                        + (f", {e.location}" if e.location else "")
                    ),
                ) from None
            except ValueError as e:
                raise ValueError(
                    f"Transform '{fn.__name__}' parameter '{parameter_name}': {e}"
                ) from None

        result = fn(*bound_arguments.args, **bound_arguments.kwargs)

        try:
            result = cast(R, spec.output_contract.validate(result))
        except ContractTypeMismatch as e:
            raise TypeError(
                f"Return value from '{fn.__name__}' must be {e.expected_type}; "
                f"got {type(result).__name__}."
            ) from None
        except SchemaCoercionError as e:
            raise SchemaCoercionError(
                e.mode,
                e.violations,
                location=(
                    f"Transform '{fn.__name__}' return value"
                    + (f", {e.location}" if e.location else "")
                ),
            ) from None
        except ValueError as e:
            raise ValueError(f"Transform '{fn.__name__}' return value: {e}") from None

        return result

    return wrapper


class Transform[**P, R]:
    def __init__(self, fn: Callable[P, R], *, side_effect: bool = False):
        self._fn = fn
        self.__transform_spec__ = _inspect_transform(fn)
        if side_effect and get_type_hints(fn).get("return") is not type(None):
            raise TypeError(
                f"Transform '{fn.__name__}' with side_effect=True must explicitly "
                "annotate its return as None."
            )
        self._side_effect = side_effect

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> R:
        return _wrap_transform(self._fn, self.__transform_spec__)(*args, **kwds)

    def get_signature(self) -> inspect.Signature:
        return inspect.signature(self._fn)

    @property
    def default_name(self) -> str | None:
        return get_callable_name(self._fn)

    @property
    def side_effect(self) -> bool:
        """Whether this transform is a skippable terminal side effect."""
        return self._side_effect


@overload
def transform[**P, R](
    f: Callable[P, R],
    *,
    side_effect: bool = False,
) -> Transform[P, R]: ...


@overload
def transform[**P, R](
    f: None = None,
    *,
    side_effect: bool = False,
) -> Callable[[Callable[P, R]], Transform[P, R]]: ...


def transform[**P, R](
    f: Callable[P, R] | None = None,
    *,
    side_effect: bool = False,
) -> Transform[P, R] | Callable[[Callable[P, R]], Transform[P, R]]:
    """Decorate a function to validate its annotated inputs and output.

    Use as ``@transform``, ``@transform()``, or
    ``@transform(side_effect=True)``. A side-effect transform must explicitly
    return ``None`` and can be skipped by ``Pipeline.run``. DataFrame contracts in
    ``Annotated`` control schema validation and coercion. Supported runtime
    classes are checked with ``isinstance`` when no contract or context marker
    applies. Each annotation can carry one recognized marker, and ``Context()``
    is available for parameters. Unrecognized metadata has no effect.

    Args:
        f: Function to decorate. Omit when using ``@transform()``.
        side_effect: Mark a terminal transform that can be skipped by a pipeline run.

    Returns:
        A callable transform that can also be added to a pipeline.

    Raises:
        TypeError: An annotation has an unsupported type or invalid markers.
    """
    if f is None:
        return lambda fn: Transform(fn, side_effect=side_effect)

    return Transform(f, side_effect=side_effect)


def side_effect[**P, R](f: Callable[P, R]) -> Transform[P, R]:
    """Mark a terminal transform as a side effect.

    This is shorthand for ``@transform(side_effect=True)``. The function must
    explicitly declare ``-> None``. Calling it directly still runs it.
    """
    return Transform(f, side_effect=True)
