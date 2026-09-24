"""Portable inspection and validation helpers for SID and MIDI files."""

from .midi import MidiFileInfo, validate_midi
from .sid import SidHeader, parse_sid

__all__ = ["MidiFileInfo", "SidHeader", "parse_sid", "validate_midi"]
__version__ = "0.1.0"
