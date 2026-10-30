# PLMS Desktop 0.2.8

This is an update of the existing PLMS Desktop 0.2.7 Tauri installer project.
It runs in a native application window using embedded WebView2. It does not
launch Microsoft Edge in app mode and has no local HTTP server.

## Build the Windows installer

1. Extract this ZIP.
2. Replace the files in your existing GitHub builder repository with the
   contents of PLMS-Desktop-0.2.8, including .github/workflows/build-windows.yml.
   Put package.json and src-tauri at the repository root, not inside an extra
   PLMS-Desktop-0.2.8 folder.
3. Commit the changes.
4. Actions > Build PLMS Local Database Desktop > Run workflow.
5. Download PLMS-Desktop-0.2.8-Windows-Installer after the workflow succeeds.
   Its NSIS .exe is the Windows installer; the ZIP supplied here is build source.

You can also use BUILD PLMS.bat on a Windows machine with the build
requirements described in README-BETA.md. Python/Node/Rust are build tools;
the installed app bundles its database worker and the installer includes
WebView2. Word desktop is needed for editing report templates.

## Changes

- Uses PLMS-Audited(1).html as its interface, preserving recent UI fixes.
- Bundles 209 catalog tests and 20 profiles. Catalog edits persist in the app's
  SQLite database. The HTML autosave/link button is removed.
- Preserves native authentication, application identity, database location,
  offline fonts, installer branding and startup reveal from 0.2.7.
- Adds permission-checked Employee and Trainee database storage. An existing
  database missing these modules receives the bundled 60 Employee / 7 Trainee
  seed without replacing clinical data or its customized catalog.
- Normal successful saves update state without re-rendering the whole UI.
- Reports' Word button has tooltip Open in Word. It creates a managed DOCX on
  first opening and launches Word directly. Saved changes are converted to
  report HTML and persisted through the authenticated database worker.
- Word conversion preserves common text, font, paragraph, table and image
  formatting. Keep {{RESULTS_TABLE}} and required merge tokens intact. Missing
  results tokens reject the edited layout, retaining the last usable template.
- New reports use the saved template. Archived finalized report versions stay
  frozen; reopen an existing preview to view the current layout where applicable.
- Do not edit the same template in Word and PLMS's visual designer simultaneously.
  After a DOCX is created, it is the Word button's managed layout source.

## Data folders

The same Tauri application identifier pk.org.sgrh.plms retains the existing
application-data location. plms_storage_paths exposes the resolved location.
The database is data/plms.sqlite3. Folders for templates, backups, exports and
Office assets remain separate from installed executable files. Word watchers
use Temp for disposable conversions and stop when the database worker exits.
Updating does not import data from the mistaken Edge-based package automatically.
If you entered new data there, export a PLMS backup before moving back to Tauri.

## Validation and limits

- All frontend workflow suites passed; 88 inline scripts and both native JS
  bridges parsed successfully.
- 47 backend tests passed, including Word permissions, managed-file preservation,
  ID validation, management storage and scope, database restart and seed migration.
- Bundled offline font references and embedded catalog counts verified.
- Tests simulate Word launch and save input; Word COM conversion, Windows launch,
  NSIS compilation and visual report parity have not been exercised in Linux.
  The actual .exe is compiled by the included Windows GitHub Actions workflow.
- Review a sample PLMS report after editing Word templates. Advanced Word-only
  drawings, section headers, tracked changes and pagination may differ in HTML.
- Back up existing PLMS data before installing an update. Use the app's backup
  workflow; also retain the managed templates folder when moving PCs.
