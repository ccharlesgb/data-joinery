from dataclasses import fields, is_dataclass
from typing import Any, get_type_hints


class Context:
    """Mark a transform parameter as supplied by the pipeline context.

    Use with ``Annotated``. By default, the parameter's type selects a field
    of the same type on the context dataclass.

    Args:
        type_: Context field type to use instead of the parameter's type.
    """

    def __init__(self, type_: type | None = None) -> None:
        self.type = type_


def inspect_context_type(context_type: type[Any]) -> dict[type, str]:
    """Return dependency types mapped to fields on a context dataclass."""
    if not isinstance(context_type, type) or not is_dataclass(context_type):
        raise TypeError(
            f"Pipeline context type must be a dataclass; got {context_type!r}. "
            "Decorate a class with @dataclass and pass that class to Pipeline()."
        )

    type_hints = get_type_hints(context_type, include_extras=True)
    fields_by_type: dict[type, str] = {}
    for field in fields(context_type):
        field_type = type_hints.get(field.name)
        if field_type is None:
            raise TypeError(
                f"Pipeline context field '{field.name}' must have a type annotation. "
                "Annotate it with the dependency class it provides."
            )
        if field_type is Any or not isinstance(field_type, type):
            raise TypeError(
                f"Pipeline context field '{field.name}' has type {field_type!r}; "
                "dependencies must use unsubscripted runtime classes. "
                "Replace this annotation with a concrete class."
            )
        if field_type in fields_by_type:
            other_field = fields_by_type[field_type]
            raise TypeError(
                f"Pipeline context fields '{other_field}' and '{field.name}' both "
                f"provide {field_type.__name__}. Keep one field per dependency type."
            )
        fields_by_type[field_type] = field.name

    return fields_by_type
