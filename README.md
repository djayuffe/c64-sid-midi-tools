# c64-sid-midi-tools

Small, dependency-free command-line tools for inspecting Commodore 64 PSID/RSID files and structurally validating Standard MIDI Files.

This project was rebuilt from an audited personal experiment folder. It deliberately does **not** claim to convert arbitrary SID audio to MIDI: that requires playback/emulation or audio transcription and cannot be implemented faithfully from a SID header alone.

## Install

```sh
python3 -m pip install .
```

## Usage

Inspect SID metadata:

```sh
c64-sid-midi inspect music.sid
```

Validate a MIDI file without needing an audio or MIDI stack:

```sh
c64-sid-midi validate-midi arrangement.mid
```

Both commands print structured JSON. Invalid or truncated input produces a clear error and exit status `2`.

## Library API

```python
from c64_sid_midi_tools import parse_sid, validate_midi

header, payload = parse_sid(open("music.sid", "rb").read())
info = validate_midi(open("arrangement.mid", "rb").read())
print(header.title, info.tracks)
```

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

See [the source audit](docs/SOURCE_AUDIT.md) for the extraction decision and what was intentionally excluded.
