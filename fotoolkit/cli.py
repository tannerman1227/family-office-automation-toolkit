"""Command line entry point.

`python -m fotoolkit run-all` regenerates every workbook, memo, table, and the
review queue. Human decisions already stored in outputs/review/decisions.json
are kept when the draft id still matches.
"""

import argparse
import sys
from pathlib import Path

from fotoolkit.config import REPO_ROOT
from fotoolkit.pipeline import build_model, write_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fotoolkit",
        description="Family Office Automation Toolkit (synthetic Harborline sample)",
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root")
    parser.add_argument("--output", type=Path, default=None, help="Where to write artifacts")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run-all", help="Regenerate every output from the sample data")
    sub.add_parser("dashboard", help="Open the Streamlit executive dashboard")
    args = parser.parse_args(argv)
    output = args.output or (args.root / "outputs")
    if args.command == "dashboard":
        app = args.root / "app" / "dashboard.py"
        os_exec_streamlit(app)
        return 0
    model = build_model(args.root)
    payload = write_outputs(model, output)
    print(payload["lede"])
    print(f"Wrote {output}")
    return 0


def os_exec_streamlit(app: Path) -> None:
    import os

    os.execv(sys.executable, [sys.executable, "-m", "streamlit", "run", str(app)])


if __name__ == "__main__":
    raise SystemExit(main())
