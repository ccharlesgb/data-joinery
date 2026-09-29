import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAX_FAILURE_OUTPUT = 8_000


def main() -> int:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout:
        print(json.dumps({"continue": True, "suppressOutput": True}))
        return 0

    check = subprocess.run(
        ["just", "check"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode:
        output = "\n".join(part for part in (check.stdout, check.stderr) if part)
        output = output[-MAX_FAILURE_OUTPUT:]
        print(f"`just check` failed:\n{output}", file=sys.stderr)
        return 2

    print(json.dumps({"continue": True, "suppressOutput": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
