"""Inspect Python annotations without loading a dataframe backend."""

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
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is Annotated and args:
        return normalize_python_type(args[0])

    if origin in (Union, UnionType) and args:
        non_none_args = [arg for arg in args if arg is not NoneType]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            return normalize_python_type(non_none_args[0])

    return python_type
