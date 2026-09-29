from dataclasses import fields, is_dataclass
from typing import Any, get_type_hints


class Context:
    """Marks a transform parameter as resolved from its pipeline context."""

    def __init__(self, type_: type | None = None) -> None:
        self.type = type_


def inspect_context_type(context_type: type[Any]) -> dict[type, str]:
    """Return dependency types mapped to fields on a context dataclass."""
    if not isinstance(context_type, type) or not is_dataclass(context_type):
        raise TypeError(
            f"pipeline context type must be a dataclass, got {context_type!r}"
        )

    type_hints = get_type_hints(context_type, include_extras=True)
    fields_by_type: dict[type, str] = {}
    for field in fields(context_type):
        field_type = type_hints.get(field.name)
        if field_type is None:
            raise TypeError(
                f"pipeline context field '{field.name}' must have a type annotation"
            )
        if field_type is Any or not isinstance(field_type, type):
            raise TypeError(
                "pipeline context dependencies must use unsubscripted runtime classes; "
                f"field '{field.name}' has type {field_type!r}"
            )
        if field_type in fields_by_type:
            other_field = fields_by_type[field_type]
            raise TypeError(
                f"pipeline context fields '{other_field}' and '{field.name}' both "
                f"provide {field_type.__name__}"
            )
        fields_by_type[field_type] = field.name

    return fields_by_type
