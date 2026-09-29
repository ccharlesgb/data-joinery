from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="data-joinery",
        description="Schema safety for DataFrame transformations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version("data-joinery"),
    )
    parser.parse_args(argv)
    parser.print_help()
