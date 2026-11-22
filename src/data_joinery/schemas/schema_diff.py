"""Shared types for schema differences."""

from dataclasses import dataclass
from typing import Literal

DifferenceKind = Literal["additional", "missing", "type_mismatch"]


@dataclass(frozen=True)
class SchemaDifference:
    """Describe one difference between an input and target schema.

    Attributes:
        kind: Whether the field is additional, missing, or has a different type.
        path: Location of the field, including nested fields and list elements.
        given: Input field type, or None when the field is missing.
        expected: Target field type, or None when the field is additional.
    """

    kind: DifferenceKind
    path: str
    given: object | None
    expected: object | None


@dataclass(frozen=True)
class SchemaDiff:
    """Group differences between an input and target schema.

    Attributes:
        additional: Input fields absent from the target schema.
        missing: Target fields absent from the input schema.
        type_mismatches: Fields whose input and target types differ.
    """

    additional: tuple[SchemaDifference, ...]
    missing: tuple[SchemaDifference, ...]
    type_mismatches: tuple[SchemaDifference, ...]
