# Native action audit and executable name

The installed application executable is now `medicsoft-plms.exe`, configured
through Tauri's mainBinaryName. Existing registered installation identity and
data locations are retained. The installer checks the previous executable for
running processes before repair, removes the old registered binary on upgrade,
and retargets its existing shortcuts using the previous MainBinaryName.

The frontend request scan found one unsupported Python action, `audit_clear`.
It now requires an authenticated session and `audit.delete`. It clears the
SQLite audit entries and their activity.jsonl mirror, resets the export cursor,
and leaves application state, accounts, credentials and recovery snapshots
intact. A failed mirror replacement rolls back the database clear. The UI clears
its browser history only after the native operation succeeds.

Office/Word integration and the Report Designer are retired. The package no
longer loads the Office adapter, imports/exports Word documents, watches Word
files, exposes Office integration controls, or dispatches Word actions. Shared
report generation, assignment, direct printing and text templates are retained.
Historical documents remain preserved by storage migration as user data.

| Area | Implemented requests matched to frontend |
| --- | --- |
| Startup and session | status, bootstrap, login, bypass_login, logout, ping |
| Database | read, commit, restore |
| Passwords | password |
| Audit history | audit, audit_clear |
| Backups | backup, snapshots, snapshot_read, snapshot_create, snapshot_import, snapshot_delete |

All 18 Python request names now have matching handlers. Direct frontend Tauri
command calls match the Rust command registry. Regression checks compare the
frontend requests with the dispatchers, including conditional action names, so
new unmatched requests fail validation.

Validation includes authenticated/unauthenticated audit clear, permission denial
and grants, retained patient data/backups/accounts, restart persistence, future
audit logging, database rollback on log failure, and frontend success/failure/
cancellation ordering. Windows packaging and upgrade testing remain separate
from these local tests; see the pull request's Windows workflow result.

## Hidden Google Drive backups — 29 October 2026

Eleven `drive_*` requests are dispatched through the existing private worker. The
native-action contract also scans google-drive.js and the shared action list.
Google requests require an active Administrator session and backup permissions;
account tokens are never exposed through the frontend status/job responses.

Cloud table export and restore use purpose-specific permission checks at request
and completed download retrieval. Cloud deletion verifies the hidden PLMS marker
before deleting the selected file; it leaves local recovery copies intact.
