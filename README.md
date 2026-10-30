# Medicsoft PLMS Windows app package

Latest build: **1.0.13 — 30 October 2026**. Based on
**PLMS-1.0.13-Collapsible-Main-Menu.html**, with the native Windows database,
login, Google Drive backups and approved installer integration retained.

Includes Files under Management, updated report template names, zoom layout
fixes, unified filter styling, Test / Profile ellipsis and reselection, the
updated Samples status filter, editable order-linked result dates, and
collapsible main menu sections. The catalog contains 192 tests and 14 profiles;
management contains 61 employees and zero embedded trainees. Existing records
and accounts are preserved.

The generated installer is **Medicsoft.PLMS_1.0.13_x64-setup.exe**.

## Build on GitHub

1. Extract this ZIP.
2. Upload the **contents inside PLMS-Build**, including `.github`, to the root of
   `nomantahirmnt/PLMS-Build`. Do not create a nested PLMS-Build folder.
3. Commit the files to `main`.
4. Open **Actions → Build Medicsoft PLMS → Run workflow**, select `main`, and run.
5. After success, open **Releases** and download the setup `.exe` and checksum.

The ZIP is source code; it does not contain a compiled Windows installer.
`BUILD-WINDOWS.ps1` is available for a local Windows build with the required
Python, Rust, Node and Visual Studio C++ tools. The build downloads the pinned official Microsoft WebView2 SDK; the installed interface needs no web assets.

## Hidden Google Drive backups

New: **Settings → Backup & Restore → Google Drive** connects a Google account,
stores backups in hidden app storage, schedules automatic uploads while the app
is running, verifies uploaded data, and stages cloud backups for the existing
full-restore confirmation. All existing local backup controls remain available.

A Google Desktop OAuth client must be registered once before users can connect.
See **[GOOGLE-DRIVE-SETUP.md](GOOGLE-DRIVE-SETUP.md)** for the build-owner secret
or installed-app setup option. No account credentials are included in this ZIP.

The latest standalone base, including Reference/Consultant/Blood Group, corrected
registration-number binding, restored confirmation dialogs, automatic trainee
serial numbers and removal of embedded trainee data, is included with native
database adapters and retired Office/Designer integrations removed.

## Included changes

- PLMS HTML with native database, login, backup and audit integration.
- Approved seven-state HTML installer/uninstaller inside NSIS, with functional folder,
  shortcut, launch, repair and removal options; real NSIS progress.
- Official Medicsoft PLMS logo on the app, setup and uninstaller icons.
- Target dialog geometry of 952 × 998 logical pixels, proportionally adjusted
  for Windows scaling and available screen space.
- Native Tauri file-drop interception disabled so in-page catalog dragging can
  receive browser events; current pointer-based reordering retained.
- Local fonts/icons and no Save Updated HTML button in the packaged app.
- One desktop window/history handler, avoiding duplicate portable handlers.

## Installation and data

| Purpose | Default path |
| --- | --- |
| Program | `C:\Program Files\Medicsoft\PLMS\` |
| Writable data | `C:\ProgramData\Medicsoft\PLMS\` |

PLMS and LIS keep separate folders. Upgrade and ordinary uninstall retain PLMS
data. Deleting data requires the explicit unchecked-by-default removal option.
The existing safe storage migration is retained; see STORAGE-MIGRATION.md.

Fresh-install sign-in: **U001 / 123**. Existing accounts and credentials remain
unchanged. Microsoft Office integration and the Report Designer are retired.

See UPDATE-2026-10-26.md, INSTALLER-THEME.md and VALIDATION.md for details.

## Google Drive backups

The Google Desktop OAuth JSON is included and automatically bundled into the
Windows backend. Users click Connect Google Drive in Backup & Restore; no setup
file selection is required. Local and Cloud rows share one recovery table, schedule
and retention control. Backup Now uploads immediately even with scheduling Off.
See GOOGLE-DRIVE-SETUP.md for build/account requirements and operating details.
