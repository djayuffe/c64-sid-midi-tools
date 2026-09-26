"""Minimal, strict validation of Standard MIDI Files (SMF).

Copyright (C) 2026 Ulf Bertilsson. SPDX-License-Identifier: GPL-3.0-or-later.
"""

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


def _encode_vlq(value: int) -> bytes:
    if not 0 <= value <= 0x0FFFFFFF:
        raise ValueError("MIDI delta time must fit in a four-byte variable-length quantity")
    result = bytearray([value & 0x7F])
    value >>= 7
    while value:
        result.append(0x80 | (value & 0x7F))
        value >>= 7
    result.reverse()
    return bytes(result)


def _validate_track(data: bytes) -> int:
    """Validate events in one track and return their count."""
    offset = 0
    running_status: int | None = None
    event_count = 0
    saw_end_of_track = False
    while offset < len(data):
        if saw_end_of_track:
            raise ValueError("MIDI track contains data after its end-of-track event")
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
            meta_type = data[offset]
            offset += 1
            length, offset = _read_vlq(data, offset)
            if offset + length > len(data):
                raise ValueError("truncated meta-event payload")
            if meta_type == 0x2F and length != 0:
                raise ValueError("MIDI end-of-track event must have an empty payload")
            offset += length
            saw_end_of_track = meta_type == 0x2F
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
    if not saw_end_of_track:
        raise ValueError("MIDI track is missing its end-of-track event")
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


@dataclass(frozen=True)
class MidiNote:
    """One note to be written to a type-0 Standard MIDI File."""

    start: int
    duration: int
    pitch: int
    velocity: int = 96
    channel: int = 0

    def __post_init__(self) -> None:
        for name, value in (("start", self.start), ("duration", self.duration), ("pitch", self.pitch),
                            ("velocity", self.velocity), ("channel", self.channel)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"MIDI note {name} must be an integer")
        if self.start < 0:
            raise ValueError("MIDI note start must not be negative")
        if self.duration <= 0:
            raise ValueError("MIDI note duration must be positive")
        if not 0 <= self.pitch <= 127:
            raise ValueError("MIDI note pitch must be in the range 0..127")
        if not 1 <= self.velocity <= 127:
            raise ValueError("MIDI note velocity must be in the range 1..127")
        if not 0 <= self.channel <= 15:
            raise ValueError("MIDI channel must be in the range 0..15")


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
    if format_type == 0 and track_count != 1:
        raise ValueError("MIDI format 0 must declare exactly one track")
    if division == 0:
        raise ValueError("MIDI timing division must not be zero")

    if division & 0x8000:
        signed_fps = division.to_bytes(2, "big", signed=False)[0] - 256
        fps = 29.97 if signed_fps == -29 else -float(signed_fps)
        if fps not in (24.0, 25.0, 29.97, 30.0):
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


def make_midi(notes: list[MidiNote], *, ticks_per_beat: int = 480, tempo_bpm: float = 120.0) -> bytes:
    """Create a format-0 MIDI file from absolute-tick note events.

    The output contains a tempo meta event and a correctly ordered note-off
    before note-on when notes meet at the same tick.
    """
    if isinstance(ticks_per_beat, bool) or not isinstance(ticks_per_beat, int) or not 1 <= ticks_per_beat <= 0x7FFF:
        raise ValueError("ticks per beat must be in the range 1..32767")
    if tempo_bpm <= 0:
        raise ValueError("tempo must be positive")
    microseconds_per_beat = round(60_000_000 / tempo_bpm)
    if not 1 <= microseconds_per_beat <= 0xFFFFFF:
        raise ValueError("tempo is outside the representable MIDI range")

    events: list[tuple[int, int, bytes]] = []
    active_until: dict[tuple[int, int], int] = {}
    for note in sorted(notes, key=lambda item: (item.start, item.channel, item.pitch, item.duration)):
        key = (note.channel, note.pitch)
        if note.start < active_until.get(key, -1):
            raise ValueError("overlapping notes with the same channel and pitch are ambiguous in MIDI")
        active_until[key] = note.start + note.duration
        events.append((note.start, 1, bytes([0x90 | note.channel, note.pitch, note.velocity])))
        events.append((note.start + note.duration, 0, bytes([0x80 | note.channel, note.pitch, 0])))
    events.sort(key=lambda event: (event[0], event[1], event[2]))

    track = bytearray(_encode_vlq(0))
    track.extend(b"\xFF\x51\x03")
    track.extend(microseconds_per_beat.to_bytes(3, "big"))
    last_tick = 0
    for tick, _, event in events:
        track.extend(_encode_vlq(tick - last_tick))
        track.extend(event)
        last_tick = tick
    track.extend(b"\x00\xFF\x2F\x00")
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x00\x00\x01" + ticks_per_beat.to_bytes(2, "big")
    return header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)


def write_midi_file(filename: str, notes: list[MidiNote], *, ticks_per_beat: int = 480, tempo_bpm: float = 120.0) -> None:
    """Create and write a validated type-0 MIDI file."""
    data = make_midi(notes, ticks_per_beat=ticks_per_beat, tempo_bpm=tempo_bpm)
    validate_midi(data)
    with open(filename, "wb") as handle:
        handle.write(data)


def inspect_midi_file(filename: str) -> MidiFileInfo:
    """Read and validate one Standard MIDI File."""
    with open(filename, "rb") as handle:
        return validate_midi(handle.read())
