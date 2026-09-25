# c64-sid-midi-tools

Dependency-free utilities for two reliable jobs:

- inspect Commodore 64 PSID/RSID file metadata; and
- create or structurally validate Standard MIDI Files (SMF).

The package is deliberately portable: it requires Python 3.10+ only—no audio driver, JACK server, MIDI device, or external Python package.

> **Scope:** a SID file contains 6502 machine code and SID register writes, not a note list. Accurate SID-to-MIDI transcription needs emulation or audio analysis, so this project does not pretend a header parser can perform that conversion. It provides dependable inspection plus MIDI authoring and validation primitives instead.

## Install

Install from a checkout:

```sh
python3 -m pip install .
```

For development without installation:

```sh
PYTHONPATH=src python3 -m c64_sid_midi_tools.cli --help
```

## Command-line usage

Every successful command writes structured JSON to standard output. Invalid files or arguments return exit status `2` and a concise error message.

### Inspect a SID file

```sh
c64-sid-midi inspect music.sid
```

The result includes the PSID/RSID magic, version, load/init/play addresses, song count, text metadata, payload size, and—where present—v2+ flags, relocation values, and second/third SID addresses. An implicit load address is decoded from the payload according to the SID specification.

### Validate an existing MIDI file

```sh
c64-sid-midi validate-midi arrangement.mid
```

Validation checks the SMF header, format/track-count rules, timing division, track chunk lengths, variable-length quantities, running status, channel-data boundaries, and the required end-of-track event. It validates file structure; it does not render or play audio.

### Create a MIDI file from JSON notes

Create `notes.json` with absolute tick positions:

```json
[
  {"start": 0, "duration": 480, "pitch": 60, "velocity": 100, "channel": 0},
  {"start": 480, "duration": 480, "pitch": 64},
  {"start": 960, "duration": 960, "pitch": 67, "channel": 1}
]
```

Then create a portable format-0 MIDI file:

```sh
c64-sid-midi make-midi notes.json melody.mid --tempo 120 --ticks-per-beat 480
c64-sid-midi validate-midi melody.mid
```

`start` is zero or greater; `duration` is positive; `pitch` is 0–127; `velocity` is 1–127 (default `96`); and `channel` is 0–15 (default `0`). Notes ending and starting at the same tick are ordered safely: the note-off is emitted first.

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

## Development and verification

```sh
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
ruff check src tests
python3 -m pip wheel --no-build-isolation --no-deps .
```

The project was extracted from an unversioned experimental folder. [SOURCE_AUDIT.md](docs/SOURCE_AUDIT.md) records the source findings and the deliberate exclusions.
