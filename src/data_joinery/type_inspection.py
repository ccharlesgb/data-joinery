"""Inspect Python annotations without loading a dataframe backend."""

from collections.abc import Callable
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

NoneType = type(None)


def is_list(tp: Any) -> bool:
    """Return whether the normalized annotation has a list origin.

    Examples:
        >>> is_list(list[int])
        True
        >>> is_list(Annotated[list[str] | None, "description"])
        True
        >>> is_list(tuple[int, ...])
        False
    """
    tp = normalize_python_type(tp)
    origin = get_origin(tp)
    return origin is list


def get_list_element_type(tp: Any) -> Any:
    """Return the element type of a normalized list annotation.

    Raises:
        ValueError: If the annotation is not a list with one type argument.

    Examples:
        >>> get_list_element_type(list[int]) is int
        True
        >>> get_list_element_type(Annotated[list[str] | None, "description"]) is str
        True
        >>> get_list_element_type(list[int | None]) == (int | None)
        True
    """
    tp = normalize_python_type(tp)
    if not is_list(tp):
        raise ValueError(f"{tp} is not a list type")
    args = get_args(tp)
    if len(args) != 1:
        raise ValueError(f"List type {tp} should have exactly one type argument")
    return args[0]


def unwrap_optional_type(python_type: Any) -> Any:
    """Remove an outer optional wrapper while preserving the wrapped annotation.

    Examples:
        >>> unwrap_optional_type(Annotated[int, "description"] | None)
        typing.Annotated[int, 'description']
        >>> unwrap_optional_type(int | str | None) == (int | str | None)
        True
    """
    if get_origin(python_type) in (Union, UnionType):
        args = get_args(python_type)
        non_none_args = [arg for arg in args if arg is not NoneType]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            return non_none_args[0]

    return python_type


def normalize_python_type(python_type: Any) -> Any:
    """Expose the underlying type for inspection, ignoring metadata and nullability.

    Remove outer Annotated and Optional (T | None) wrappers repeatedly.
    Leave other unions and annotations inside containers unchanged.

    Examples:
        >>> normalize_python_type(Annotated[int | None, "description"]) is int
        True
        >>> normalize_python_type(int | str) == (int | str)
        True
        >>> normalize_python_type(list[int | None]) == list[int | None]
        True
    """
    if get_origin(python_type) is Annotated:
        return normalize_python_type(get_args(python_type)[0])

    unwrapped_type = unwrap_optional_type(python_type)
    if unwrapped_type is not python_type:
        return normalize_python_type(unwrapped_type)

    return python_type


def _resolve_literal[NativeType](
    annotation: Any, resolve: Callable[[type], NativeType], backend_name: str
) -> NativeType:
    values = get_args(annotation)
    if not values:
        raise ValueError("Literal type must include at least one value")

    resolved = {resolve(type(value)) for value in values}
    if len(resolved) != 1:
        raise ValueError(
            f"Literal values must resolve to a single {backend_name} type: {annotation}"
        )
    return next(iter(resolved))
