# Source audit

## Input

The supplied `Ai_coded` folder contains 103 Python files and 21 shell scripts, with no Git repository, package metadata, documentation, or tests.

## Findings

- Four Python files fail syntax compilation: one has indentation damage and three contain shell syntax saved as Python.
- Many scripts are successive, unversioned experiments with overlapping MIDI-generation or JACK/ALSA logic.
- Several scripts create hardware clients, enter infinite loops, or parse command-line arguments at import time. They are unsuitable as importable package modules.
- Several SID-to-MIDI scripts reference undefined functions and variables or third-party libraries without dependency metadata. None provided a testable general SID-to-MIDI implementation.
- A non-project personal GUI and host-specific audio/ALSA/JACK utilities were out of scope and excluded to prevent accidental publication of unrelated material.

## Result

`c64-sid-midi-tools` is a new, independent, dependency-free package. It retains only the sound ideas that could be validated safely:

- strict PSID/RSID header inspection, including implicit load addresses;
- strict Standard MIDI File structure validation;
- a documented CLI and automated regression tests.

## Follow-up hardening

The maintained project received a second audit after extraction. It added:

- PSID/RSID version rules and v2+ extension-field parsing;
- SMF format-0 track-count, end-of-track, and malformed-meta-event validation;
- a dependency-free, validated format-0 MIDI writer; and
- command and API examples for every maintained capability.

The original folder is unchanged. No source file was copied verbatim into this project. The omitted experimental scripts are intentionally not represented as supported features.

## Maintained-code audit — 2026-09-26

The public-release audit reviewed the maintained parser, MIDI writer/validator,
CLI, package metadata and documentation. It corrected four issues before
publication:

- v3/v4 extra-SID address bytes now have to decode to PSID-defined extra-SID
  windows, rather than any `$Dxxx` I/O location;
- note fields are explicitly integer-only and same-channel/same-pitch overlaps
  are rejected as ambiguous MIDI authoring input;
- CLI errors now use standard error, leaving standard output machine-readable
  JSON on successful commands; and
- package metadata, source headers and repository files now declare
  GPL-3.0-or-later with copyright © 2026 Ulf Bertilsson.

The audit did not broaden scope to SID emulation or transcription. The
documented boundary remains intentional and is reflected in the README.
