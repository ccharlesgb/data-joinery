"""Inspect Python annotations without loading a dataframe backend."""

from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

NoneType = type(None)


def is_list(tp: Any) -> bool:
    tp = normalize_python_type(tp)
    origin = get_origin(tp)
    return origin is list


def get_list_element_type(tp: Any) -> Any:
    tp = normalize_python_type(tp)
    if not is_list(tp):
        raise ValueError(f"{tp} is not a list type")
    args = get_args(tp)
    if len(args) != 1:
        raise ValueError(f"List type {tp} should have exactly one type argument")
    return args[0]


def normalize_python_type(python_type: Any) -> Any:
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is Annotated and args:
        return normalize_python_type(args[0])

    if origin in (Union, UnionType) and args:
        non_none_args = [arg for arg in args if arg is not NoneType]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            return normalize_python_type(non_none_args[0])

    return python_type
