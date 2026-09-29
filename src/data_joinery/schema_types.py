from dataclasses import dataclass
from typing import Literal

CoercionMode = Literal["project_cast", "project", "project_top_level", "strict"]
DifferenceKind = Literal["additional", "missing", "type_mismatch"]


@dataclass(frozen=True)
class SchemaDifference:
    kind: DifferenceKind
    path: str
    given: object | None
    expected: object | None


@dataclass(frozen=True)
class SchemaDiff:
    additional: tuple[SchemaDifference, ...]
    missing: tuple[SchemaDifference, ...]
    type_mismatches: tuple[SchemaDifference, ...]


def _format_schema_difference(difference: SchemaDifference) -> str:
    if difference.kind == "missing":
        return f"- {difference.path} (expected {difference.expected})"
    if difference.kind == "additional":
        return f"- {difference.path} (given {difference.given})"
    return f"- {difference.path}: {difference.given} -> {difference.expected}"


def _format_schema_coercion_error(
    mode: CoercionMode, violations: tuple[SchemaDifference, ...]
) -> str:
    groups: tuple[tuple[DifferenceKind, str], ...] = (
        ("missing", "Missing fields"),
        ("additional", "Additional fields"),
        (
            "type_mismatch",
            "Unsupported type casts" if mode == "project_cast" else "Type mismatches",
        ),
    )
    lines = [f"Cannot coerce dataframe using mode '{mode}':"]
    for kind, heading in groups:
        differences = [
            difference for difference in violations if difference.kind == kind
        ]
        if not differences:
            continue
        lines.append(f"  {heading}:")
        lines.extend(
            f"    {_format_schema_difference(difference)}" for difference in differences
        )
    return "\n".join(lines)


class SchemaCoercionError(Exception):
    def __init__(
        self, mode: CoercionMode, violations: tuple[SchemaDifference, ...]
    ) -> None:
        self.mode = mode
        self.violations = violations
        super().__init__(_format_schema_coercion_error(mode, violations))
