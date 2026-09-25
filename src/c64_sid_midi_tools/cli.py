"""Command-line interface for the portable inspection tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .midi import MidiNote, inspect_midi_file, write_midi_file
from .sid import inspect_sid_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="c64-sid-midi", description="Inspect C64 SID files and validate MIDI files.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (("inspect", "inspect PSID/RSID metadata"), ("validate-midi", "validate a Standard MIDI File")):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("file", type=Path)
    create = subparsers.add_parser("make-midi", help="create a type-0 MIDI file from JSON note events")
    create.add_argument("notes", type=Path, help="JSON array of note objects")
    create.add_argument("output", type=Path, help="MIDI file to create")
    create.add_argument("--tempo", type=float, default=120.0, help="tempo in beats per minute (default: 120)")
    create.add_argument("--ticks-per-beat", type=int, default=480, help="MIDI timing resolution (default: 480)")
    return parser


def _load_notes(filename: Path) -> list[MidiNote]:
    with filename.open(encoding="utf-8") as handle:
        raw_notes = json.load(handle)
    if not isinstance(raw_notes, list):
        raise ValueError("notes JSON must contain an array")
    notes = []
    for index, raw_note in enumerate(raw_notes):
        if not isinstance(raw_note, dict):
            raise ValueError(f"note {index} must be an object")
        try:
            notes.append(MidiNote(
                start=raw_note["start"],
                duration=raw_note["duration"],
                pitch=raw_note["pitch"],
                velocity=raw_note.get("velocity", 96),
                channel=raw_note.get("channel", 0),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid note {index}: {exc}") from exc
    return notes


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_sid_file(str(args.file)).to_dict()
        elif args.command == "validate-midi":
            result = inspect_midi_file(str(args.file)).to_dict()
        else:
            notes = _load_notes(args.notes)
            write_midi_file(str(args.output), notes, ticks_per_beat=args.ticks_per_beat, tempo_bpm=args.tempo)
            result = {"notes": len(notes), "output": str(args.output), "tempo_bpm": args.tempo, "ticks_per_beat": args.ticks_per_beat}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
