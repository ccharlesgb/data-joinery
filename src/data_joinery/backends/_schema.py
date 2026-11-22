"""Shared schema traversal and field compilation for built-in backends."""

from collections.abc import Callable, Iterator, Sequence
from typing import Any

from ..schemas.model_schema import ModelSchema
from ..schemas.schema_diff import (
    Field,
    ListElement,
    SchemaDiff,
    SchemaDifference,
    SchemaPath,
)


def compare_schema[NativeType](
    given: Sequence[tuple[str, NativeType]],
    expected: Sequence[tuple[str, NativeType]],
    *,
    struct_fields: Callable[[NativeType], Sequence[tuple[str, NativeType]] | None],
    list_element: Callable[[NativeType], NativeType | None],
) -> SchemaDiff:
    """Compare schemas recursively through struct fields and list elements.

    Args:
        given: Input field names and native types.
        expected: Target field names and native types.
        struct_fields: Function returning a struct's fields, or None.
        list_element: Function returning a list's element type, or None.

    Returns:
        Additional, missing, and mismatched fields in traversal order.
    """
    additional: list[SchemaDifference] = []
    missing: list[SchemaDifference] = []
    mismatches: list[SchemaDifference] = []

    def walk_types(source: NativeType, target: NativeType, path: SchemaPath) -> None:
        source_fields = struct_fields(source)
        target_fields = struct_fields(target)
        if source_fields is not None and target_fields is not None:
            walk_fields(source_fields, target_fields, path)
            return

        source_element = list_element(source)
        target_element = list_element(target)
        if source_element is not None and target_element is not None:
            walk_types(source_element, target_element, (*path, ListElement()))
        elif source != target:
            mismatches.append(SchemaDifference("type_mismatch", path, source, target))

    def walk_fields(
        source_fields: Sequence[tuple[str, NativeType]],
        target_fields: Sequence[tuple[str, NativeType]],
        parent_path: SchemaPath,
    ) -> None:
        source_names = {name for name, _ in source_fields}
        target_by_name = dict(target_fields)

        for name, source in source_fields:
            path = (*parent_path, Field(name))
            if name in target_by_name:
                walk_types(source, target_by_name[name], path)
            else:
                additional.append(SchemaDifference("additional", path, source, None))

        for name, target in target_fields:
            if name not in source_names:
                missing.append(
                    SchemaDifference(
                        "missing", (*parent_path, Field(name)), None, target
                    )
                )

    walk_fields(given, expected, ())
    return SchemaDiff(tuple(additional), tuple(missing), tuple(mismatches))


def compile_fields[NativeType](
    schema: ModelSchema[Any],
    resolve: Callable[[Any], NativeType],
    backend_name: str,
) -> Iterator[tuple[str, NativeType]]:
    """Compile model fields into native backend types.

    Args:
        schema: Model fields to compile.
        resolve: Function converting an annotation to a native type.
        backend_name: Backend name to include in compilation errors.

    Yields:
        Each field's column name and compiled native type.

    Raises:
        ValueError: If a field annotation cannot be compiled.
    """
    for field in schema.fields:
        try:
            field_type = resolve(field.annotation)
        except ValueError as error:
            raise ValueError(
                f"Schema '{schema.model.__name__}' field '{field.name}' "
                f"({field.annotation!r}): {error}. Use a supported Python "
                f"type or an Annotated {backend_name} type."
            ) from error
        yield field.name, field_type
