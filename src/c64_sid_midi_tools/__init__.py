"""Portable inspection and validation helpers for SID and MIDI files.

Copyright (C) 2026 Ulf Bertilsson. SPDX-License-Identifier: GPL-3.0-or-later.
"""

from .midi import MidiFileInfo, MidiNote, make_midi, validate_midi, write_midi_file
from .sid import SidHeader, parse_sid

__all__ = ["MidiFileInfo", "MidiNote", "SidHeader", "make_midi", "parse_sid", "validate_midi", "write_midi_file"]
__version__ = "0.2.0"
