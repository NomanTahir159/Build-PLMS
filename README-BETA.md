# PLMS Desktop 0.2.12

Built from the supplied `PLMS-Duty-Roster-Direct-Print(1).html` using the established Tauri 2 desktop package and private SQLite backend.

## Build the Windows installer with GitHub Actions

1. Extract this ZIP. Copy all contents of `PLMS-Desktop-0.2.12` to the root of your existing builder repository, including the hidden `.github` folder.
2. Commit the files. Open **Actions → Build PLMS Local Database Desktop → Run workflow**.
3. Download **PLMS-Desktop-0.2.12-Windows-Installer** from the completed run.
4. Extract the artifact and run the Windows x64 `.exe`. The artifact also contains a SHA-256 checksum.

The archive is the complete builder source, not a precompiled installer. Windows installer compilation runs on GitHub's Windows runner.

## Initial account

| Setting | Value |
|---|---|
| Name | Noman Tahir |
| User ID | U001 |
| Password | 123 |

Fresh installations create exactly one account. There are no bundled Technologist, Pathologist, Developer, or other extra accounts. Enter **Noman Tahir** or **U001** as the username, including on the first login. Passwords are stored as salted PBKDF2 hashes. Later password changes remain in effect after restarting.

Existing installed databases and their real accounts are preserved on upgrade. The single-account rule applies to bundled defaults and fresh initialization; it does not silently delete accounts from a working laboratory database.

## Installation and storage

The default installation directory is **C:\Program Files\PLMS**. Installation requires Windows administrator permission. Runtime data is written to the existing per-user PLMS application-data directory, including `data/plms.sqlite3`; the app does not write laboratory records into Program Files. The existing identifier `pk.org.sgrh.plms` and publisher Medicsoft Corporation are retained.

- `src`: supplied application, embedded catalog/profile rules, native adapters, offline fonts.
- `backend`: private database worker and management seed.
- `src-tauri`: Windows shell, native title bar, icons and installer.
- `frontend` and `backend/tests`: automated checks run before packaging.
- `.github/workflows`: Windows build and artifact upload.

## Requested changes

- Native title bar follows PLMS Light, Dark and System theme modes, including at initial window reveal.
- Catalog Auto Save, Import and Export toolbar buttons are removed. Catalog edits save through the app's database.
- All 270 tests and profile/rule metadata in the uploaded catalog are bundled.
- Uploaded UI and workflows are retained, including admin-only Bypass Processing. The database validates processing-bypass eligibility as well as the frontend.
- Existing backup/restore remains connected to the private backend. Runtime icon fonts are available offline.

## Local build

On Windows, run `BUILD PLMS.bat` with Python 3.13, Rust and the Visual Studio C++ build tools installed. The workflow pins Tauri CLI 2.12.0 and PyInstaller 6.22.3. Resource generation builds the database worker before compiling the installer. There is no separate first-time account setup wizard.

See `VALIDATION.md` for completed checks and Windows validation still required.

## Login corrections in 0.2.12

Bypass Login now persists in the database for eligible Administrator/Developer accounts. Enable it under Edit User and save; the next app start creates a normal backend session without showing the login form. The initial setting remains Off. Disabling the option restores manual sign-in. Explicit Sign Out stays signed out until the next app launch or manual login. Password changes still require the current password, and normal session expiry and authorization checks remain.

Save User waits for database confirmation before showing a success message. Rejected writes report their error and keep the dialog open. Login fields keep the same neutral surface during focus and autofill in both themes, and the native window waits for the startup sign-in decision before appearing.

## Session Limits (0.2.12)
Settings places Session Limits after Accent Color, with three cards per desktop row. Administrators may configure inactivity (Never, 5/15/30/60/120/240 minutes) and maximum duration (Never, 1/2/4/8/12/24 hours). Defaults remain 30 minutes and 8 hours. Both the desktop adapter and private backend enforce the stored limits; Never disables only the selected limit. Keyboard, pointer, scrolling, touch, and management-frame activity count as activity. Windows installer compilation and visual verification require the GitHub Windows build.

Recent workflow audit: incomplete Save edits to Processed/Restored results now clear submission timestamps and return the item to Results Entry; complete verification edits remain pending. An edit-only verifier may perform this transition in the backend. Patient Name now has the same required marker as Lab Number. 64 backend tests and frontend integration checks passed.
