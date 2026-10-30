# Shared Medicsoft folders — PLMS only

Program default: `C:\Program Files\Medicsoft\PLMS\`.
Writable data: `C:\ProgramData\Medicsoft\PLMS\`.
Existing custom installation directories remain selectable. Upgrading an old standard `Program Files\Medicsoft PLMS` installation selects the new standard folder. Bundle ID, product name, release delivery, seeds, application screens, accounts and branding are unchanged.

| Folder | Program Files\Medicsoft\PLMS | ProgramData\Medicsoft\PLMS |
|---|---|---|
| Root | Packaged Python/SQLite worker | EBWebView, Temp, backup index and migration receipt |
| System | HTML, JS and CSS | — |
| Resources | Logos, icons, fonts and licenses | — |
| Catalog | Bundled catalog seed | Current catalog projection from SQLite |
| Presets | Bundled defaults | Configured presets, settings and Word documents |
| Database | — | Authoritative plms.sqlite3 database and WAL/SHM |
| Backup | — | Local snapshots and legacy recovery copies |
| Log | — | Activity history, diagnostics and migration summary |

The main application executable and uninstaller remain at the program installation root. Resource references use Tauri's actual resource directory, so a custom program installation also works. **Settings → About → Data Folder** opens the writable PLMS root, not its parent and never LIS.

## Migration and recovery

Close older PLMS before installing or starting the new package. Keep a separate backup until you have verified the upgrade.

Supported legacy roots are exactly:

- `%PROGRAMDATA%\Medicsoft PLMS`
- `%APPDATA%\pk.org.sgrh.plms` and `%LOCALAPPDATA%\pk.org.sgrh.plms`
- `%APPDATA%\Medicsoft PLMS` and `%LOCALAPPDATA%\Medicsoft PLMS`

Within each, supported database names are `Database\plms.sqlite3`, `data\plms.sqlite3` and `plms.sqlite3`. No LIS or shared Medicsoft directory is searched. Development/test database paths do not trigger machine-data migration.

If the new database exists, it is never replaced—even an empty or invalid existing file is left for manual review. A missing destination plus more than one legacy database stops startup and lists the candidates in diagnostics. No newest-file heuristic, automatic merge or automatic selection is used. To resolve ambiguity, retain every original and have the administrator select and restore one coherent PLMS database/backup while PLMS is closed.

For a single candidate, ancillary files are copied first. The database is read through SQLite in read-only mode and copied with `Connection.backup()`, including committed WAL data and excluding uncommitted work. The temporary destination must pass SQLite `quick_check`; a same-volume, exclusive hard link publishes the completed file atomically. This requires a local filesystem supporting hard links (the standard NTFS ProgramData volume does). A publication race cannot overwrite a destination. Original databases, WAL files, backups and documents are never moved or deleted by migration. A configured legacy account store is marked as already initialized in the destination so the normal default-account seed cannot reset its accounts or password hashes.

Selected-database Backup/backups files keep their names when free. Existing files always win. Conflicts are copied under `Backup\Legacy\<source-id>\Conflicts`; backups from other legacy roots are retained under their own `Backup\Legacy\<source-id>` directory. Catalog, Presets, Log and managed Word files from the selected root are copied without replacement. Older `Templates` documents are retained in `Presets\Word`. These files do not merge database records; SQLite remains authoritative.

`Root\storage-migration.json` records successfully processed roots so later launches do not resurrect backups you deleted in PLMS. `Log\storage-migration.json` is a diagnostic summary. If a previously migrated destination database disappears, PLMS asks for recovery instead of silently recreating it. An interrupted migration may retain temporary/recovery files. If `Root\storage-migration.lock` remains, close all PLMS processes, preserve the files, inspect the diagnostics and remove only that stale lock before retrying. Migration errors stop database startup rather than creating an unrelated empty installation.

## Upgrades and uninstall

Ordinary upgrades and uninstall do not delete data. The uninstaller's unchecked-by-default **Delete app data** option runs the packaged worker with a fixed PLMS-only deletion allowlist. It accepts no caller-supplied directory, never targets the shared Medicsoft parent and never targets a LIS sibling. It is skipped for `/UPDATE`. Directory links/junctions are not traversed into another application's data. Failed cleanup reports that recovery files remain.

The installer grants normal users modify permission on the PLMS data directory only. It does not change LIS permissions. Shared parent folders are retained, even when otherwise empty.

## Validation

The package adds SQLite WAL, no-overwrite/race, corrupt/ambiguous source, backup collision, repeat-launch, missing-database recovery, link isolation and explicit deletion tests. Installer source checks cover standard/custom upgrade paths, guarded deletion, resources, WebView and Word paths. PRs run the existing frontend/backend checks and build the Windows NSIS installer. Manual runs retain GitHub Releases delivery; no Actions artifact storage is introduced.

Local validation cannot substitute for installing on a Windows PC. Before rollout, test an upgrade with a copied real PLMS database, verify a few patient reports/accounts, create a backup, open Data Folder, and uninstall without selecting data deletion. Keep LIS installed throughout that check.
