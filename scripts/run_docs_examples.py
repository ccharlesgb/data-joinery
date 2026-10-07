from __future__ import annotations

import re
import runpy
import subprocess
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DOCS_SOURCE_DIRECTORY = REPOSITORY_ROOT / "docs_src"
DOCS_DIRECTORY = REPOSITORY_ROOT / "docs"
MAX_WORKERS = 8
SNIPPET = re.compile(r'--8<-- "(docs_src/[^"\n]+)"')


def validate_snippets() -> None:
    """Keep every displayed backend example and its generated output together."""
    for page in DOCS_DIRECTORY.rglob("*.md"):
        references = {
            reference.split(":", 1)[0]
            for reference in SNIPPET.findall(page.read_text())
        }
        for reference in references:
            path = REPOSITORY_ROOT / reference
            if not path.is_file():
                raise FileNotFoundError(f"{page}: missing snippet {reference}")
            if path.suffix == ".py":
                for backend, other_backend in (
                    ("spark", "polars"),
                    ("polars", "spark"),
                ):
                    if not path.stem.endswith(f"_{backend}"):
                        continue
                    partner = path.with_name(
                        f"{path.stem.removesuffix(f'_{backend}')}_{other_backend}.py"
                    )
                    if (
                        partner.exists()
                        and str(partner.relative_to(REPOSITORY_ROOT)) not in references
                    ):
                        raise ValueError(
                            f"{page}: missing {other_backend} tab for {reference}"
                        )


def _report_failure(
    script_path: Path, result: subprocess.CompletedProcess[str]
) -> None:
    stdout = result.stdout.rstrip() or "<empty>"
    stderr = result.stderr.rstrip() or "<empty>"
    print(
        f"\n{script_path} exited with {result.returncode}\n"
        f"--- stdout ---\n{stdout}\n"
        f"--- stderr ---\n{stderr}",
        file=sys.stderr,
    )


def write_log(script_path: Path, stream_name: str, content: str) -> None:
    log_path = script_path.with_name(f"{script_path.stem}_{stream_name}.log")
    if content:
        log_path.write_text(content)
    elif log_path.exists():
        log_path.unlink()


def run_python_example(script_path: Path) -> subprocess.CompletedProcess[str]:
    stdout = StringIO()
    stderr = StringIO()

    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            runpy.run_path(str(script_path), run_name="__main__")
    except Exception:  # noqa: BLE001 - report example failures like a subprocess would
        with redirect_stderr(stderr):
            traceback.print_exc()
        return subprocess.CompletedProcess(
            [sys.executable, str(script_path)],
            returncode=1,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    return subprocess.CompletedProcess(
        [sys.executable, str(script_path)],
        returncode=0,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def run_example(script_path: Path) -> None:
    print(f"Running {script_path}", flush=True)
    is_test = script_path.name.startswith("test_")
    if is_test:
        executable = [
            sys.executable,
            "-m",
            "pytest",
            "-rn",
            "--show-capture=stdout",
        ]
        result = subprocess.run(
            executable + [str(script_path)],
            capture_output=True,
            check=False,
            cwd=REPOSITORY_ROOT,
            text=True,
        )
    else:
        result = run_python_example(script_path)

    if not is_test:
        write_log(script_path, "stdout", result.stdout)
        if result.returncode != 0:
            _report_failure(script_path, result)
        assert result.returncode == 0, f"{script_path} exited with {result.returncode}"
    else:
        std_out_no_duration = re.sub(
            r" in \d+(?:\.\d+)?s(?= ={2,}\n)", "", result.stdout
        )
        write_log(script_path, "stdout", std_out_no_duration)
        if result.returncode != 0:
            _report_failure(script_path, result)
        assert result.returncode == 0, (
            f"Tests at {script_path} exited with {result.returncode}"
        )


def main() -> None:
    script_paths = sorted(DOCS_SOURCE_DIRECTORY.rglob("*.py"))
    python_examples = [
        path for path in script_paths if not path.name.startswith("test_")
    ]
    test_examples = [path for path in script_paths if path.name.startswith("test_")]

    # stdout and stderr redirection is process-global, so ordinary examples must run
    # sequentially. Keeping them in this process allows PySpark's getOrCreate() to
    # reuse its active Spark session instead of starting a JVM for every script.
    for script_path in python_examples:
        run_example(script_path)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(executor.map(run_example, test_examples))

    validate_snippets()


if __name__ == "__main__":
    main()
