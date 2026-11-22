"""Validate schema differences against coercion rules."""

from collections.abc import Callable
from typing import Literal, get_args

from .schema_diff import SchemaDiff, SchemaDifference

CoercionMode = Literal["project_cast", "project", "project_top_level", "strict"]


def check_coercion_mode(mode: CoercionMode) -> None:
    """Check that a coercion mode is supported.

    Args:
        mode: Coercion mode to check.

    Raises:
        ValueError: If the mode is unsupported.
    """
    if mode not in get_args(CoercionMode):
        raise ValueError(
            f"Unsupported coercion mode {mode!r}. Choose 'strict', 'project', "
            "'project_top_level', or 'project_cast'."
        )


def find_coercion_violations(
    diff: SchemaDiff,
    mode: CoercionMode,
    can_cast: Callable[[object | None, object | None], bool],
) -> tuple[SchemaDifference, ...]:
    """Find schema differences that the selected coercion mode forbids.

    Args:
        diff: Differences between the input and target schemas.
        mode: Rules for projection and casting.
        can_cast: Backend function checking whether a type cast is supported.

    Returns:
        Violations in missing, additional, then type-mismatch order. An empty
        tuple means the differences are permitted by the coercion mode.
    """
    additional = ()
    mismatches = diff.type_mismatches
    match mode:
        case "strict":
            additional = diff.additional
        case "project_top_level":
            additional = tuple(item for item in diff.additional if len(item.path) > 1)
        case "project":
            pass
        case "project_cast":
            mismatches = tuple(
                item for item in mismatches if not can_cast(item.given, item.expected)
            )

    return (*diff.missing, *additional, *mismatches)
