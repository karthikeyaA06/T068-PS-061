"""Run a JSONL command file through the PS-061 pharmacy services."""

import argparse
import sys
from pathlib import Path

from app.commands.command_processor import CommandProcessor, build_default_handlers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process one PS-061 JSON command per line (JSONL)."
    )
    parser.add_argument("input_file", help="Path to the UTF-8 JSONL command file.")
    parser.add_argument(
        "-o", "--output",
        help="Optional output JSONL path. Defaults to standard output.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.is_file():
        parser.error(f"Input file does not exist: {input_path}")

    processor = CommandProcessor(build_default_handlers())
    try:
        with input_path.open("r", encoding="utf-8") as source:
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w", encoding="utf-8", newline="\n") as target:
                    failures = processor.process_stream(source, target)
            else:
                failures = processor.process_stream(source, sys.stdout)
    except OSError as exc:
        print(f"Command-file I/O error: {exc}", file=sys.stderr)
        return 2

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
