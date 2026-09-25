# Contributing

Keep the package dependency-free and portable. New functionality must be usable without audio hardware, MIDI hardware, or a running JACK/ALSA service.

Before opening a change, run:

```sh
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
ruff check src tests
```

Please add regression coverage for parsing, validation, or generated binary output. Do not add a feature that claims general SID-to-MIDI transcription unless it includes an explicit emulation or signal-analysis implementation and test corpus.
