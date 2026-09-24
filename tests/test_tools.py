from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from c64_sid_midi_tools.cli import main
from c64_sid_midi_tools.midi import validate_midi
from c64_sid_midi_tools.sid import parse_sid


def minimal_sid(*, implicit_load: bool = False) -> bytes:
    header = bytearray(0x76)
    header[:4] = b"PSID"
    header[4:6] = (2).to_bytes(2, "big")
    header[6:8] = (0x76).to_bytes(2, "big")
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
    def test_parses_sid_metadata_and_payload(self) -> None:
        header, payload = parse_sid(minimal_sid())
        self.assertEqual(header.magic, "PSID")
        self.assertEqual(header.title, "Unit Test")
        self.assertEqual(header.load_address, 0x1000)
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

    def test_cli_inspects_sid_and_validates_midi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sid_file = Path(directory) / "sample.sid"
            midi_file = Path(directory) / "sample.mid"
            sid_file.write_bytes(minimal_sid())
            midi_file.write_bytes(minimal_midi())
            self.assertEqual(main(["inspect", str(sid_file)]), 0)
            self.assertEqual(main(["validate-midi", str(midi_file)]), 0)
            self.assertEqual(json.loads(json.dumps(parse_sid(sid_file.read_bytes())[0].to_dict()))["title"], "Unit Test")


if __name__ == "__main__":
    unittest.main()
