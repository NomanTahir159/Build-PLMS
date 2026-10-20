# Package validation

Base: uploaded `PLMS-Optimized(2).html`. Native authentication, SQLite persistence, Word integration, custom title bar, navigation and corrected installer are retained from the previous Tauri package.

Bundled data matches the upload: 234 unique test codes, 15 registered profiles, 61 employees and 9 trainees. Supplied ordering, definitions, reference rules and management records are preserved. No dummy patient/order/result data is seeded. The only initial account is U001 / Noman Tahir / 123, accepting either name or ID.

Validation:

- All 12 frontend workflow suites passed, covering authentication, bypass, native controls, patient/order dates, samples, results, approval, sessions and permissions; 111 host inline scripts compiled.
- All 72 database tests passed, including a fresh install with the actual embedded data, catalog/employee edits, restart persistence and the Catalog JSON projection.
- All 8 installer source/artwork checks passed.
- Embedded management scripts compile; runtime-only saved dropdowns, iframe documents and generated dialogs are removed so installation initializes fresh bindings without duplicates.
- Catalog Save Updated HTML, Import, Export and Auto Save controls and the standalone HTML export handler are excluded.
- Offline font/icon assets and ZIP integrity checked.

The ZIP contains build source. GitHub Actions compiles the Windows x64 Python worker, Rust host and NSIS setup executable, then uploads the installer and SHA-256 checksum. Windows compilation and visual execution of the app/installer/uninstaller were not performed in this Linux environment. The build is unsigned.
