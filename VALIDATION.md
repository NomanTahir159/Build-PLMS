# Package validation

The package uses the latest `PLMS-Refresh-Modal-Corners-Fixed.html` as its frontend source, with the native login, SQLite, Word and desktop-window integrations applied. Catalog data is identical to the embedded catalog: 265 unique tests and 22 profiles. Only U001 / Noman Tahir / 123 is seeded on a fresh installation.

Passed locally:

- All frontend workflow suites: authentication, bypass settings, navigation, flush-before-close, sample transitions, result submission/approval, chronology, patient dates and session limits.
- All 71 backend tests, including native snapshot deletion tests for: database/file deletion, restart persistence, rejected invalid/stale IDs and unauthorized deletion.
- Eight installer source/artwork checks, including geometry at multiple scaling factors, callback coverage, matching image resources, and rejection of runtime color variables in SetCtlColors.
- Source script syntax, offline font assets, catalog preservation, installer resource paths and ZIP integrity.

This is a GitHub build source package, not a compiled Windows executable. GitHub Actions builds the Python worker, Rust host and NSIS installer and supplies the setup EXE with a SHA-256 checksum. Actual Windows compilation, installer/uninstaller execution, light/dark rendering, printing and DPI visual inspection were not available in this Linux preparation environment. The app is not code-signed.
