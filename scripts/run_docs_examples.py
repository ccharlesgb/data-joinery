from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DOCS_SOURCE_DIRECTORY = REPOSITORY_ROOT / "docs_src"
MAX_WORKERS = 8


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
    else:
        executable = [sys.executable]
    result = subprocess.run(
        executable + [str(script_path)],
        capture_output=True,
        check=False,
        cwd=REPOSITORY_ROOT,
        text=True,
    )

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
        if result.returncode > 1:
            _report_failure(script_path, result)
        assert result.returncode <= 1, (
            f"Tests at {script_path} exited with {result.returncode}"
        )


def main() -> None:
    script_paths = sorted(DOCS_SOURCE_DIRECTORY.rglob("*.py"))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(executor.map(run_example, script_paths))


if __name__ == "__main__":
    main()
