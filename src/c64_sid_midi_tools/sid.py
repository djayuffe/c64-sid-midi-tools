"""Strict, dependency-free PSID/RSID header parsing.

Copyright (C) 2026 Ulf Bertilsson. SPDX-License-Identifier: GPL-3.0-or-later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

_MIN_HEADER_SIZE = 0x76
_EXTENDED_HEADER_SIZE = 0x7C
_KNOWN_MAGICS = {b"PSID", b"RSID"}


def _u16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def _u32be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def _text(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("latin-1", errors="replace").rstrip()


def _extra_sid_address(raw_address: int, label: str) -> int | None:
    """Decode and validate a PSID v3/v4 extra-SID address byte.

    The header stores an address divided by 16.  Valid extra chips occupy the
    documented I/O ranges $D420-$D7E0 and $DE00-$DFE0, never the primary
    $D400 SID window or arbitrary I/O locations.
    """
    if raw_address == 0:
        return None
    address = 0xD000 + (raw_address << 4)
    if 0xD420 <= address <= 0xD7E0 or 0xDE00 <= address <= 0xDFE0:
        return address
    raise ValueError(f"{label} SID address ${address:04X} is outside the valid PSID ranges")


@dataclass(frozen=True)
class SidHeader:
    """Metadata and address information from a PSID or RSID header."""

    magic: str
    version: int
    data_offset: int
    load_address: int
    init_address: int
    play_address: int
    songs: int
    start_song: int
    speed: int
    title: str
    author: str
    released: str
    flags: int | None
    relocation_start_page: int | None
    relocation_pages: int | None
    second_sid_address: int | None
    third_sid_address: int | None
    payload_size: int

    def to_dict(self) -> dict[str, int | str]:
        """Return JSON-safe metadata suitable for a CLI or API response."""
        return asdict(self)


def parse_sid(data: bytes) -> tuple[SidHeader, bytes]:
    """Parse a PSID/RSID file and return its header and machine-code payload.

    A zero load address indicates that the first two bytes of the payload encode
    the little-endian load address, per the SID file specification.
    """
    if len(data) < _MIN_HEADER_SIZE:
        raise ValueError("SID file is shorter than the mandatory 118-byte header")
    if data[:4] not in _KNOWN_MAGICS:
        raise ValueError("not a PSID or RSID file")

    magic = data[:4]
    version = _u16be(data, 4)
    if version not in (1, 2, 3, 4):
        raise ValueError(f"unsupported SID version {version}")
    if magic == b"RSID" and version == 1:
        raise ValueError("RSID version 1 is not defined")

    data_offset = _u16be(data, 6)
    minimum_offset = _EXTENDED_HEADER_SIZE if version >= 2 else _MIN_HEADER_SIZE
    if not minimum_offset <= data_offset <= len(data):
        raise ValueError("SID data offset is outside the file")

    payload = data[data_offset:]
    load_address = _u16be(data, 8)
    if load_address == 0:
        if len(payload) < 2:
            raise ValueError("SID file has an implicit load address but no payload")
        load_address = int.from_bytes(payload[:2], "little")
        payload = payload[2:]

    songs = _u16be(data, 14)
    start_song = _u16be(data, 16)
    if songs == 0:
        raise ValueError("SID file declares zero songs")
    if not 1 <= start_song <= songs:
        raise ValueError("SID start-song number is outside the declared song range")

    flags = _u16be(data, 0x76) if version >= 2 else None
    second_sid = _extra_sid_address(data[0x7A], "second") if version >= 3 else None
    third_sid = _extra_sid_address(data[0x7B], "third") if version >= 4 else None
    if second_sid == third_sid and second_sid is not None:
        raise ValueError("second and third SID addresses must differ")

    header = SidHeader(
        magic=magic.decode("ascii"),
        version=version,
        data_offset=data_offset,
        load_address=load_address,
        init_address=_u16be(data, 10),
        play_address=_u16be(data, 12),
        songs=songs,
        start_song=start_song,
        speed=_u32be(data, 18),
        title=_text(data[22:54]),
        author=_text(data[54:86]),
        released=_text(data[86:118]),
        flags=flags,
        relocation_start_page=data[0x78] if version >= 2 else None,
        relocation_pages=data[0x79] if version >= 2 else None,
        second_sid_address=second_sid,
        third_sid_address=third_sid,
        payload_size=len(payload),
    )
    return header, payload


def inspect_sid_file(filename: str) -> SidHeader:
    """Read and parse one SID file."""
    with open(filename, "rb") as handle:
        header, _ = parse_sid(handle.read())
    return header
