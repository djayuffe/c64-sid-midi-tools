"""Minimal, strict validation of Standard MIDI Files (SMF)."""

from __future__ import annotations

from dataclasses import dataclass


def _u32be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def _read_vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for count in range(4):
        if offset >= len(data):
            raise ValueError("truncated variable-length quantity")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, offset
    raise ValueError("variable-length quantity exceeds four bytes")


def _validate_track(data: bytes) -> int:
    """Validate events in one track and return their count."""
    offset = 0
    running_status: int | None = None
    event_count = 0
    while offset < len(data):
        _, offset = _read_vlq(data, offset)
        if offset >= len(data):
            raise ValueError("track ends after a delta time")
        first = data[offset]
        if first < 0x80:
            if running_status is None:
                raise ValueError("MIDI data byte appears without a running status")
            status = running_status
        else:
            status = first
            offset += 1

        if status == 0xFF:
            running_status = None
            if offset >= len(data):
                raise ValueError("truncated meta event")
            offset += 1  # meta-event type
            length, offset = _read_vlq(data, offset)
            if offset + length > len(data):
                raise ValueError("truncated meta-event payload")
            offset += length
        elif status in (0xF0, 0xF7):
            running_status = None
            length, offset = _read_vlq(data, offset)
            if offset + length > len(data):
                raise ValueError("truncated SysEx payload")
            offset += length
        elif 0x80 <= status <= 0xEF:
            running_status = status
            needed = 1 if status >> 4 in (0xC, 0xD) else 2
            if offset + needed > len(data):
                raise ValueError("truncated MIDI channel event")
            if any(byte >= 0x80 for byte in data[offset : offset + needed]):
                raise ValueError("MIDI channel event contains a status byte as data")
            offset += needed
        else:
            raise ValueError(f"unsupported system status byte 0x{status:02X}")
        event_count += 1
    return event_count


@dataclass(frozen=True)
class MidiFileInfo:
    """Structural information obtained while validating an SMF."""

    format: int
    tracks: int
    ticks_per_beat: int | None
    frames_per_second: float | None
    ticks_per_frame: int | None
    event_count: int

    def to_dict(self) -> dict[str, int | float | None]:
        return {
            "format": self.format,
            "tracks": self.tracks,
            "ticks_per_beat": self.ticks_per_beat,
            "frames_per_second": self.frames_per_second,
            "ticks_per_frame": self.ticks_per_frame,
            "event_count": self.event_count,
        }


def validate_midi(data: bytes) -> MidiFileInfo:
    """Validate a complete Standard MIDI File and return its structure.

    This validator intentionally has no playback dependencies. It verifies SMF
    chunks, VLQs, running status, and channel-event data boundaries.
    """
    if len(data) < 14 or data[:4] != b"MThd" or _u32be(data, 4) != 6:
        raise ValueError("not a Standard MIDI File with a six-byte header")
    format_type = int.from_bytes(data[8:10], "big")
    track_count = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if format_type not in (0, 1, 2):
        raise ValueError("unsupported MIDI format")
    if track_count == 0:
        raise ValueError("MIDI file declares zero tracks")
    if division == 0:
        raise ValueError("MIDI timing division must not be zero")

    if division & 0x8000:
        signed_fps = division.to_bytes(2, "big", signed=False)[0] - 256
        fps = -float(signed_fps)
        if fps not in (24.0, 25.0, 29.0, 30.0):
            raise ValueError("invalid SMPTE frames-per-second division")
        ticks_per_beat, ticks_per_frame = None, division & 0xFF
    else:
        fps, ticks_per_frame, ticks_per_beat = None, None, division

    offset = 14
    event_count = 0
    for _ in range(track_count):
        if offset + 8 > len(data) or data[offset : offset + 4] != b"MTrk":
            raise ValueError("missing MIDI track chunk")
        length = _u32be(data, offset + 4)
        offset += 8
        if offset + length > len(data):
            raise ValueError("truncated MIDI track chunk")
        event_count += _validate_track(data[offset : offset + length])
        offset += length
    if offset != len(data):
        raise ValueError("unexpected trailing bytes after MIDI tracks")
    return MidiFileInfo(format_type, track_count, ticks_per_beat, fps, ticks_per_frame, event_count)


def inspect_midi_file(filename: str) -> MidiFileInfo:
    """Read and validate one Standard MIDI File."""
    with open(filename, "rb") as handle:
        return validate_midi(handle.read())
