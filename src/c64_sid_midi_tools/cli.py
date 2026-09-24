"""Command-line interface for the portable inspection tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .midi import inspect_midi_file
from .sid import inspect_sid_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="c64-sid-midi", description="Inspect C64 SID files and validate MIDI files.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (("inspect", "inspect PSID/RSID metadata"), ("validate-midi", "validate a Standard MIDI File")):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = inspect_sid_file(str(args.file)) if args.command == "inspect" else inspect_midi_file(str(args.file))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
