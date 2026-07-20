# CHANGELOG

## [Unreleased]

### Added
- Documented session progress in `CLAUDE.md`.
- Created `CHANGELOG.md` to track future releases.

### Fixed
- Corrected `core/printer.py` printer DC creation to use `CreateDC()` then `CreatePrinterDC()`.

### Updated
- Refined interface layout and preview behavior to support a professional Windows desktop appearance.
- Confirmed printing integration with `pywin32` and validated printer listing.

### Notes
- Current printing state may still raise "Unable to open printer" depending on Windows printer access and configuration.
