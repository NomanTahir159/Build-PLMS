# Package validation

Base: `PLMS-Grouped-Deduplicated-Report-Notes.html`. The current standalone changes are integrated into the established Tauri Windows package, preserving native login, SQLite persistence, theme-aware custom title bar, navigation, Medicsoft installer artwork and folder layout.

Bundled data matches the latest HTML exactly: 192 tests, 14 registered profiles, 61 employees and 9 trainees. Fresh installs have no demo patients, orders or results. The initial account remains Noman Tahir / U001, password 123.

Checks completed in the preparation environment:

- 15 frontend suites passed, including all six result-action navigation paths, one-loop closure, failed/canceled actions, note grouping/deduplication and repeat pagination, note template overlays, authentication, bypass, native controls, patient dates, samples, sessions and permissions. 111 executable host scripts compiled.
- 73 database tests passed. A new integration case verifies a results user without order-edit permission can save scoped notes and the result-save timestamp, then reopen the database with notes and the exact typed decimal string retained.
- 8 installer source/artwork checks passed.
- Embedded catalog and management data match the source; 31 management scripts compile. No duplicate host IDs or saved runtime bindings remain.
- Catalog Import, Export, Auto Save and Save Updated HTML controls, the HTML export handler and its unused compressed source copy are excluded. Native catalog persistence remains enabled.
- ZIP integrity and required build/workflow entries verified.

The ZIP contains source for GitHub Actions to compile the Windows x64 Python worker, Rust host and NSIS setup executable. Windows compilation, installation, uninstallation and visual execution were not performed here. The build is unsigned. Existing installations retain their data.
