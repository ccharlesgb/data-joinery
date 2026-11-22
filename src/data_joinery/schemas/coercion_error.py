"""Exceptions and readable messages for schema coercion failures."""

from .coercion import CoercionMode
from .schema_diff import SchemaDifference


def _format_schema_difference(difference: SchemaDifference, mode: CoercionMode) -> str:
    if difference.kind == "missing":
        return (
            f"Missing field '{difference.path}': expected {difference.expected}. "
            "Add the field or update the model."
        )
    if difference.kind == "additional":
        action = (
            "Remove it or add it to the model."
            if mode == "strict"
            else "Remove it or use 'project' to drop nested extra fields."
        )
        return f"Additional field '{difference.path}': got {difference.given}. {action}"
    action = (
        "Convert the values to the expected type before coercion."
        if mode == "project_cast"
        else "Change the field type or use 'project_cast' if a cast is valid."
    )
    return (
        f"Field '{difference.path}': expected {difference.expected}, "
        f"got {difference.given}. {action}"
    )


def _format_schema_coercion_error(
    mode: CoercionMode,
    violations: tuple[SchemaDifference, ...],
    location: str | None,
) -> str:
    prefix = f"{location}: " if location else ""
    lines = [f"{prefix}Cannot coerce DataFrame (mode='{mode}'):"]
    for kind in ("missing", "additional", "type_mismatch"):
        lines.extend(
            f"  - {_format_schema_difference(difference, mode)}"
            for difference in violations
            if difference.kind == kind
        )
    return "\n".join(lines)


class SchemaCoercionError(Exception):
    """Report schema differences that violate a coercion mode.

    Attributes:
        mode: Coercion mode that rejected the input schema.
        violations: Schema differences that caused the failure.
        location: Optional context identifying where coercion failed.
    """

    def __init__(
        self,
        mode: CoercionMode,
        violations: tuple[SchemaDifference, ...],
        *,
        location: str | None = None,
    ) -> None:
        """Build an error describing the schema violations.

        Args:
            mode: Coercion mode that rejected the input schema.
            violations: Differences that violate the mode's rules.
            location: Optional context included before the error message.
        """
        self.mode = mode
        self.violations = violations
        self.location = location
        super().__init__(_format_schema_coercion_error(mode, violations, location))
