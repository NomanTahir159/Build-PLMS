# Medicsoft PLMS — Windows build package

Version 1.0.0 · App version 2026 · Developer: Noman Tahir

This source package builds the Medicsoft PLMS Windows x64 installer through GitHub Actions. It is based on `PLMS-Catalog-Action-Order(1).html` supplied on 20 October 2026, preserving its 265 tests and 22 profiles. No Windows executable is precompiled in this ZIP.

## Build the installer

1. Extract the ZIP into a GitHub repository. Include `.github`, `.gitignore` and `.gitattributes`; do not upload the ZIP itself as repository source. GitHub Desktop or `git add -A` includes these files.
2. Push the complete extracted contents to GitHub.
3. Open **Actions → Build Medicsoft PLMS → Run workflow**.
4. Download **Medicsoft-PLMS-1.0.0-Windows-Installer** from the successful run. Extract and run the generated `*-setup.exe`. Its SHA-256 checksum is included.

Alternatively, on Windows with Rust/MSVC and Python installed, run `BUILD PLMS.bat`. The workflow installs its own build dependencies. The installer includes the offline WebView2 runtime installer.

## First sign-in

Name: **Noman Tahir** or User ID: **U001**. Password: **123**.

Only this account is seeded. An existing installation retains its database, credentials and user-created accounts. Fresh installs contain no demo patients, orders, results, inventory, employees or trainees. Bypass Login and Bypass Processing remain configurable in PLMS.

## Installed folders

Program files default to `C:\Program Files\Medicsoft PLMS` (another install location can be selected). Writable records are separated into `C:\ProgramData\Medicsoft PLMS` so application upgrades do not overwrite them.

| Folder | Location and contents |
| --- | --- |
| Root | Installed backend runtime; ProgramData/Root contains EBWebView, temporary runtime files and backup ownership metadata. |
| Backup | ProgramData/Backup contains complete local recovery snapshots as JSON files. |
| Catalog | Program Files/Catalog contains the bundled seed; ProgramData/Catalog/catalog.json records current tests, profiles, order and rule edits. |
| Database | ProgramData/Database/plms.sqlite3 is the authoritative patient/order/result/account/configuration database, with SQLite WAL files. |
| Log | ProgramData/Log/activity.jsonl stores committed activity history; diagnostics.log records backend errors. |
| Resources | Program Files/Resources contains Medicsoft artwork and offline fonts/icons. |
| System | Program Files/System contains the HTML, desktop JavaScript and CSS. |
| Presets | Program Files/Presets describes bundled defaults; ProgramData/Presets/presets.json stores configured templates/settings; Presets/Word contains managed Word files. |

Catalog and preset JSON files are managed projections of SQLite. Edit them through PLMS; manually editing a projection does not bypass database validation. Local snapshots also remain indexed in SQLite and are mirrored into Backup. The installer retains ProgramData on upgrades and ordinary uninstall. The uninstaller's explicit **Delete app data** option removes it.

Earlier desktop SQLite databases in the prior user's Roaming application-data location are migrated with SQLite's backup API on first launch when the new database does not exist. Keep the earlier installation's backups until the new installation is checked. Development runs use a separate Development data folder.

## Desktop controls

The existing PLMS header is the custom title bar. **Back** and **Forward** sit after the existing actions/user area, followed by Minimize, Maximize/Restore and Close. The title bar follows PLMS light/dark colors. Back/Forward respects app permissions, is disabled at navigation boundaries and resets at logout. Closing waits for native writes and uses the PLMS unsaved-changes confirmation when applicable.

The Catalog Import, Export and Auto Save controls are removed. Catalog changes persist through the native SQLite backend and Catalog folder without linking an HTML file. Other backup/restore and report features remain available according to account permissions.

## Verification

See VALIDATION.md. Windows compilation, installer execution and visual verification run on Windows; they have not been performed in the Linux preparation environment. The package is not code-signed.
