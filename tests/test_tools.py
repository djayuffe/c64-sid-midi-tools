from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from c64_sid_midi_tools.cli import main
from c64_sid_midi_tools.midi import MidiNote, make_midi, validate_midi
from c64_sid_midi_tools.sid import parse_sid


def minimal_sid(*, implicit_load: bool = False) -> bytes:
    header = bytearray(0x7C)
    header[:4] = b"PSID"
    header[4:6] = (2).to_bytes(2, "big")
    header[6:8] = (0x7C).to_bytes(2, "big")
    header[8:10] = (0 if implicit_load else 0x1000).to_bytes(2, "big")
    header[10:12] = (0x1000).to_bytes(2, "big")
    header[14:16] = (1).to_bytes(2, "big")
    header[16:18] = (1).to_bytes(2, "big")
    header[22:32] = b"Unit Test\0"
    return bytes(header) + (b"\x00\x10" if implicit_load else b"") + b"\x60"


def minimal_midi() -> bytes:
    track = b"\x00\xFF\x2F\x00"
    return b"MThd" + (6).to_bytes(4, "big") + b"\x00\x00\x00\x01\x01\xE0" + b"MTrk" + len(track).to_bytes(4, "big") + track


class ToolTests(unittest.TestCase):
    def test_cli_reports_version(self) -> None:
        with self.assertRaises(SystemExit) as result:
            main(["--version"])
        self.assertEqual(result.exception.code, 0)

    def test_parses_sid_metadata_and_payload(self) -> None:
        header, payload = parse_sid(minimal_sid())
        self.assertEqual(header.magic, "PSID")
        self.assertEqual(header.title, "Unit Test")
        self.assertEqual(header.load_address, 0x1000)
        self.assertEqual(header.flags, 0)
        self.assertEqual(payload, b"\x60")

    def test_reads_implicit_sid_load_address(self) -> None:
        header, payload = parse_sid(minimal_sid(implicit_load=True))
        self.assertEqual(header.load_address, 0x1000)
        self.assertEqual(payload, b"\x60")

    def test_rejects_invalid_sid_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a PSID"):
            parse_sid(b"NOPE" + b"\0" * 200)
        raw = bytearray(minimal_sid())
        raw[16:18] = (2).to_bytes(2, "big")
        with self.assertRaisesRegex(ValueError, "start-song"):
            parse_sid(bytes(raw))
        raw = bytearray(minimal_sid())
        raw[4:6] = (5).to_bytes(2, "big")
        with self.assertRaisesRegex(ValueError, "unsupported SID version"):
            parse_sid(bytes(raw))

    def test_parses_extended_sid_addresses(self) -> None:
        raw = bytearray(minimal_sid())
        raw[4:6] = (4).to_bytes(2, "big")
        raw[0x7A] = 0x42
        raw[0x7B] = 0x44
        header, _ = parse_sid(bytes(raw))
        self.assertEqual((header.second_sid_address, header.third_sid_address), (0xD420, 0xD440))

    def test_rejects_invalid_extra_sid_addresses(self) -> None:
        raw = bytearray(minimal_sid())
        raw[4:6] = (4).to_bytes(2, "big")
        raw[0x7A] = 0x40  # $D400 is the primary SID window, never an extra SID.
        with self.assertRaisesRegex(ValueError, "outside the valid PSID ranges"):
            parse_sid(bytes(raw))

    def test_validates_minimal_midi(self) -> None:
        info = validate_midi(minimal_midi())
        self.assertEqual((info.format, info.tracks, info.ticks_per_beat, info.event_count), (0, 1, 480, 1))

    def test_rejects_malformed_midi(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated MIDI track"):
            validate_midi(minimal_midi()[:-1])
        with self.assertRaisesRegex(ValueError, "zero tracks"):
            raw = bytearray(minimal_midi())
            raw[10:12] = b"\0\0"
            validate_midi(bytes(raw))
        without_eot = minimal_midi()[:-4]
        without_eot = without_eot[:18] + (0).to_bytes(4, "big")
        with self.assertRaisesRegex(ValueError, "missing its end-of-track"):
            validate_midi(without_eot)

    def test_midi_writer_creates_valid_ordered_file(self) -> None:
        data = make_midi([
            MidiNote(start=480, duration=480, pitch=62),
            MidiNote(start=0, duration=480, pitch=60, velocity=100, channel=1),
        ], tempo_bpm=150)
        info = validate_midi(data)
        self.assertEqual((info.format, info.tracks, info.event_count), (0, 1, 6))
        with self.assertRaisesRegex(ValueError, "duration"):
            MidiNote(start=0, duration=0, pitch=60)
        with self.assertRaisesRegex(ValueError, "integer"):
            MidiNote(start=0.5, duration=1, pitch=60)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            make_midi([MidiNote(start=0, duration=20, pitch=60), MidiNote(start=10, duration=20, pitch=60)])

    def test_cli_inspects_sid_and_validates_midi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sid_file = Path(directory) / "sample.sid"
            midi_file = Path(directory) / "sample.mid"
            sid_file.write_bytes(minimal_sid())
            midi_file.write_bytes(minimal_midi())
            self.assertEqual(main(["inspect", str(sid_file)]), 0)
            self.assertEqual(main(["validate-midi", str(midi_file)]), 0)
            notes_file = Path(directory) / "notes.json"
            output_file = Path(directory) / "created.mid"
            notes_file.write_text('[{"start": 0, "duration": 240, "pitch": 60}]', encoding="utf-8")
            self.assertEqual(main(["make-midi", str(notes_file), str(output_file), "--tempo", "100"]), 0)
            self.assertEqual(validate_midi(output_file.read_bytes()).event_count, 4)
            self.assertEqual(json.loads(json.dumps(parse_sid(sid_file.read_bytes())[0].to_dict()))["title"], "Unit Test")

    def test_cli_errors_use_stderr_and_keep_stdout_clean(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["inspect", "missing.sid"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
