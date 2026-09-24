"""Strict, dependency-free PSID/RSID header parsing."""

from __future__ import annotations

from dataclasses import asdict, dataclass

_MIN_HEADER_SIZE = 0x76
_KNOWN_MAGICS = {b"PSID", b"RSID"}


def _u16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def _u32be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def _text(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("latin-1", errors="replace").rstrip()


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

    data_offset = _u16be(data, 6)
    if not _MIN_HEADER_SIZE <= data_offset <= len(data):
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

    header = SidHeader(
        magic=data[:4].decode("ascii"),
        version=_u16be(data, 4),
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
        payload_size=len(payload),
    )
    return header, payload


def inspect_sid_file(filename: str) -> SidHeader:
    """Read and parse one SID file."""
    with open(filename, "rb") as handle:
        header, _ = parse_sid(handle.read())
    return header
