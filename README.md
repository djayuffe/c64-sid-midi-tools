# c64-sid-midi-tools

Copyright © 2026 Ulf Bertilsson · GPL-3.0-or-later

Dependency-free utilities for two reliable jobs:

- inspect Commodore 64 PSID/RSID file metadata; and
- create or structurally validate Standard MIDI Files (SMF).

The package is deliberately portable: it requires Python 3.10+ only—no audio driver, JACK server, MIDI device, or external Python package.

> **Scope:** a SID file contains 6502 machine code and SID register writes, not a note list. Accurate SID-to-MIDI transcription needs emulation or audio analysis, so this project does not pretend a header parser can perform that conversion. It provides dependable inspection plus MIDI authoring and validation primitives instead.

## Why this exists

SID metadata tools and MIDI file tools are often mixed into host-specific audio
experiments. This package deliberately keeps the useful, portable parts:

- parse and validate PSID/RSID headers without executing unknown 6502 code;
- build a small, deterministic MIDI file from an explicit note list; and
- reject malformed MIDI before it reaches a DAW, player or hardware device.

It is therefore suitable for scripts, CI checks, data preparation and teaching
tools. It is not a SID emulator, audio player, MIDI device driver or general
SID-to-MIDI transcriber.

## Install

Install from a checkout:

```sh
python3 -m pip install .
```

For development without installation:

```sh
PYTHONPATH=src python3 -m c64_sid_midi_tools.cli --help
```

Check the installed version with `c64-sid-midi --version`.

Run directly from a clone without installing:

```sh
PYTHONPATH=src python3 -m c64_sid_midi_tools.cli inspect path/to/tune.sid
```

## Command-line usage

Every successful command writes structured JSON to standard output. Invalid files or arguments return exit status `2` and a concise error message.

### Inspect a SID file

```sh
c64-sid-midi inspect music.sid
```

The result includes the PSID/RSID magic, version, load/init/play addresses, song count, text metadata, payload size, and—where present—v2+ flags, relocation values, and second/third SID addresses. An implicit load address is decoded from the payload according to the SID specification.

The parser rejects malformed headers early, including an invalid song range,
undefined RSID v1, impossible data offsets, duplicate extra-SID locations and
extra-SID addresses outside the PSID-defined I/O windows. It does not execute
the payload.

### Validate an existing MIDI file

```sh
c64-sid-midi validate-midi arrangement.mid
```

Validation checks the SMF header, format/track-count rules, timing division, track chunk lengths, variable-length quantities, running status, channel-data boundaries, and the required end-of-track event. It validates file structure; it does not render or play audio.

### Create a MIDI file from JSON notes

Use the bundled example or create a `notes.json` file with absolute tick positions:

```json
[
  {"start": 0, "duration": 480, "pitch": 60, "velocity": 100, "channel": 0},
  {"start": 480, "duration": 480, "pitch": 64},
  {"start": 960, "duration": 960, "pitch": 67, "channel": 1}
]
```

Then create a portable format-0 MIDI file:

```sh
c64-sid-midi make-midi examples/melody.json melody.mid --tempo 120 --ticks-per-beat 480
c64-sid-midi validate-midi melody.mid
```

`start` is zero or greater; `duration` is positive; `pitch` is 0–127; `velocity` is 1–127 (default `96`); and `channel` is 0–15 (default `0`). Notes ending and starting at the same tick are ordered safely: the note-off is emitted first.

Overlapping notes with the same pitch and channel are rejected because their
note-off semantics are ambiguous in ordinary MIDI devices. Use a different
channel if overlapping same-pitch notes are intentional.

## CLI reference

| Command | Input | Output | Exit status |
| --- | --- | --- | --- |
| `inspect FILE.sid` | PSID/RSID binary | JSON header metadata | `0` or `2` |
| `validate-midi FILE.mid` | Standard MIDI File | JSON structural summary | `0` or `2` |
| `make-midi NOTES.json OUT.mid` | JSON note array | format-0 MIDI plus JSON summary | `0` or `2` |

Successful output is formatted JSON on standard output, making it safe to
consume from scripts. Diagnostics go to standard error. `make-midi` supports
`--tempo BPM` and `--ticks-per-beat PPQN`; PPQN is constrained to 1–32767.

### JSON note schema

Each note object must contain integer `start`, `duration` and `pitch` fields.
`velocity` and `channel` are optional integers.

| Field | Type | Range | Meaning |
| --- | --- | --- | --- |
| `start` | integer | 0 or higher | Absolute MIDI tick at which the note starts. |
| `duration` | integer | 1 or higher | Length in MIDI ticks. |
| `pitch` | integer | 0–127 | MIDI note number. |
| `velocity` | integer | 1–127 | Note-on velocity; defaults to 96. |
| `channel` | integer | 0–15 | MIDI channel; defaults to 0. |

## Python API

### SID inspection

```python
from pathlib import Path
from c64_sid_midi_tools import parse_sid

header, payload = parse_sid(Path("music.sid").read_bytes())
print(header.title, hex(header.load_address), len(payload))
```

### MIDI creation and validation

```python
from pathlib import Path
from c64_sid_midi_tools import MidiNote, make_midi, validate_midi

data = make_midi([
    MidiNote(start=0, duration=480, pitch=60),
    MidiNote(start=480, duration=480, pitch=64, velocity=100),
], tempo_bpm=120)
info = validate_midi(data)
Path("melody.mid").write_bytes(data)
print(info.tracks, info.ticks_per_beat)
```

`write_midi_file()` is also available when writing directly to disk is preferable.

## Format support and limits

| Capability | Supported |
| --- | --- |
| PSID | Versions 1–4 |
| RSID | Versions 2–4 |
| SID metadata | Header fields, payload, implicit load address, v2+ extension fields |
| MIDI validation | SMF formats 0, 1, and 2; PPQN and valid SMPTE timing |
| MIDI generation | Format 0, one track, tempo meta-event, note on/off events |
| SID audio rendering or arbitrary SID-to-MIDI transcription | Not implemented; requires a separate emulation or transcription engine |

## Validation guarantees

`validate-midi` reads the complete file and checks:

- the exact six-byte SMF header and legal format/track-count combinations;
- PPQN or legal SMPTE timing division;
- every track chunk's declared length and absence of trailing bytes;
- delta-time and meta/SysEx variable-length quantities;
- channel-event payload sizes and running-status use; and
- a single terminal end-of-track event with no later data.

`make-midi` validates its own output before writing. Generated files are
format 0 with one track, one tempo event and correctly ordered note events.

## Security and portability

The library only reads the files named by the caller and does not execute SID
payloads, invoke shell commands, talk to MIDI hardware, open audio devices or
download dependencies. It uses Python's standard library and supports Python
3.10 or newer.

## Development and verification

```sh
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
ruff check src tests
python3 -m pip wheel --no-build-isolation --no-deps .
```

The project was extracted from an unversioned experimental folder. [SOURCE_AUDIT.md](docs/SOURCE_AUDIT.md) records the source findings and the deliberate exclusions. The maintained-code audit also corrected extra-SID address validation, MIDI same-note overlap handling, integer validation, and CLI standard-error diagnostics.

## Project notes

- [CHANGELOG.md](CHANGELOG.md) records user-visible changes.
- [CONTRIBUTING.md](CONTRIBUTING.md) explains the portability and verification rules.
- [examples/melody.json](examples/melody.json) is a ready-to-run MIDI authoring input.
- [NOTICE](NOTICE) records Ulf Bertilsson's copyright; [LICENSE](LICENSE) and
  [COPYING](COPYING) contain the canonical GPL-3.0-or-later terms.
