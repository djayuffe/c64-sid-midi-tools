# Changelog

## Unreleased

- Licensed the project under GPL-3.0-or-later; added copyright notice for Ulf Bertilsson.
- Rejected invalid PSID v3/v4 extra-SID I/O addresses instead of reporting arbitrary I/O addresses as SID chips.
- Rejected ambiguous overlapping same-pitch/channel note pairs during MIDI creation.
- Enforced integer note fields and sent CLI diagnostics to standard error.
- Expanded usage, JSON schema, validation and security documentation.

## 0.2.0 — 2026-09-25

- Added type-0 MIDI generation from JSON note events.
- Added SID v2+ extension-field parsing and validation.
- Strengthened SMF validation for format rules, malformed events, and end-of-track handling.
- Expanded CLI, API, and format-support documentation.

## 0.1.0 — 2026-09-25

- Initial audited extraction: PSID/RSID inspection and SMF structural validation.
