from collections.abc import Callable


def get_callable_name(callable: Callable) -> str | None:
    """Return a callable's name, or its class name if it has no __name__.

    Return None for lambdas, whose name does not identify their behavior.

    Examples:
        >>> def transform():
        ...     pass
        >>> get_callable_name(transform)
        'transform'
        >>> get_callable_name(lambda: None) is None
        True
        >>> class Transform:
        ...     def __call__(self):
        ...         pass
        >>> get_callable_name(Transform())
        'Transform'
    """
    name_attr: str | None = None
    if hasattr(callable, "__name__"):
        name_attr = callable.__name__
        if name_attr == "<lambda>":
            name_attr = None
    elif hasattr(callable, "__class__"):
        name_attr = callable.__class__.__name__

    return name_attr
