"""PLMS-only, non-destructive migration into ProgramData/Medicsoft/PLMS.

Never open an old database for writing, copy a live main file, merge databases,
or replace an existing destination. SQLite backup includes committed WAL data.
"""
import hashlib
from contextlib import closing
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


class MigrationError(RuntimeError):
    pass


def data_root():
    base = os.environ.get('PROGRAMDATA')
    if not base:
        raise MigrationError('Windows ProgramData is unavailable.')
    return Path(base) / 'Medicsoft' / 'PLMS'


def legacy_roots():
    roots = []
    if os.environ.get('PROGRAMDATA'):
        roots.append(Path(os.environ['PROGRAMDATA']) / 'Medicsoft PLMS')
    for variable in ('APPDATA', 'LOCALAPPDATA'):
        if os.environ.get(variable):
            base = Path(os.environ[variable])
            roots.extend((base / 'pk.org.sgrh.plms', base / 'Medicsoft PLMS'))
    return list(dict.fromkeys(roots))


def linked(path):
    return path.is_symlink() or (getattr(path, 'is_junction', lambda: False)())


def safe_file(path, root):
    return path.is_file() and not any(linked(p) for p in (path, *path.parents)) and path.resolve().is_relative_to(root.resolve())


def publish_copy(source, target):
    """Publish a complete same-volume file without ever replacing target."""
    if any(linked(p) for p in (target, *target.parents)):
        raise MigrationError('Migration destination must not contain a symbolic link or junction.')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.plms-migrate-', dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as out, source.open('rb') as incoming:
            shutil.copyfileobj(incoming, out)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temporary, target)
            return True
        except FileExistsError:
            return False
    finally:
        temporary.unlink(missing_ok=True)


def preserve_existing_accounts(database):
    """Mark a configured legacy installation as configured, without resetting users."""
    tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'app_state', 'credentials'} <= tables:
        return
    row = database.execute('SELECT body FROM app_state WHERE id=1').fetchone()
    if not row:
        return
    try:
        users = json.loads(row[0]).get('users', [])
    except (ValueError, AttributeError):
        raise MigrationError('Legacy account state requires manual review.') from None
    configured = any(isinstance(user, dict) and database.execute('SELECT 1 FROM credentials WHERE id=?', (str(user.get('id')),)).fetchone() for user in users)
    if configured:
        database.execute('CREATE TABLE IF NOT EXISTS local_defaults(key TEXT PRIMARY KEY)')
        for key in ('default_admin_v1', 'default_admin_name_v2'):
            database.execute('INSERT OR IGNORE INTO local_defaults(key) VALUES(?)', (key,))


def database_backup(source, target):
    if any(linked(p) for p in (target, *target.parents)):
        raise MigrationError('Migration database location must not contain a symbolic link or junction.')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.plms-database-', suffix='.sqlite3', dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        # mode=ro still reads committed WAL; immutable=1 would incorrectly skip it.
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True, timeout=15)) as incoming, closing(sqlite3.connect(temporary)) as outgoing:
            elapsed = 0
            def progress(status, remaining, total):
                nonlocal elapsed
                if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                    elapsed += 1
                    if elapsed >= 150:
                        raise MigrationError('Legacy database is busy. Close older PLMS and retry.')
            incoming.backup(outgoing, pages=256, progress=progress, sleep=0.1)
            preserve_existing_accounts(outgoing)
            outgoing.commit()
            outgoing.execute('PRAGMA journal_mode=DELETE')
            if outgoing.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise MigrationError('Legacy database did not pass SQLite integrity verification.')
        with temporary.open('r+b') as file:
            os.fsync(file.fileno())
        try:
            os.link(temporary, target)
            return True
        except FileExistsError:
            return False
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def copy_tree(source, target, recovery):
    if not source.is_dir() or linked(source):
        return
    for path in sorted(source.rglob('*')):
        if not safe_file(path, source):
            continue
        relative = path.relative_to(source)
        destination = target / relative
        if destination.exists():
            if safe_file(destination, target) and digest(path) == digest(destination):
                continue
            destination = recovery / relative
            if destination.exists():
                if safe_file(destination, recovery) and digest(path) == digest(destination):
                    continue
                destination = destination.with_name(destination.name + '.' + digest(path)[:16])
        publish_copy(path, destination)


def migrate_storage(database, roots=None):
    database = Path(database)
    root = database.parent.parent
    # Never sweep user data into development/test databases.
    if roots is None:
        if not os.environ.get('PROGRAMDATA') or root.resolve() != data_root().resolve():
            return
        roots = legacy_roots()
    roots = [Path(p) for p in dict.fromkeys(roots) if Path(p).resolve() != root.resolve() and Path(p).is_dir() and not linked(Path(p))]
    if not roots and not (root / 'Root' / 'storage-migration.json').exists():
        return
    for parent in (root, *root.parents):
        if linked(parent):
            raise MigrationError('PLMS data location must not be a symbolic link or junction.')
    runtime = root / 'Root'
    runtime.mkdir(parents=True, exist_ok=True)
    lock = runtime / 'storage-migration.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise MigrationError('PLMS migration is already running or was interrupted. Close PLMS, retain recovery files, and check Root/storage-migration.lock before retrying.') from None
    os.close(fd)
    try:
        receipt = runtime / 'storage-migration.json'
        completed = []
        if receipt.exists():
            try:
                completed = json.loads(receipt.read_text(encoding='utf-8'))['legacy_roots_retained']
                if not isinstance(completed,list): raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise MigrationError('PLMS migration receipt is invalid. Retain the files and review it before retrying.') from None
            if not database.exists():
                raise MigrationError('The previously migrated PLMS database is missing. Restore it from recovery; migration will not silently recreate it.')
        roots = [old for old in roots if str(old.resolve()) not in completed]
        if not roots:
            return
        candidates = []
        for old in roots:
            for relative in ('Database/plms.sqlite3', 'data/plms.sqlite3', 'plms.sqlite3'):
                path = old / relative
                if safe_file(path, old):
                    candidates.append((old, path))
        selected = None
        existed = database.exists()
        if not existed:
            if len(candidates) > 1:
                raise MigrationError('Multiple legacy PLMS databases found. No database was selected or merged. Retain the originals and choose one manually: ' + '; '.join(str(p) for _, p in candidates))
            if candidates:
                selected, source = candidates[0]
        for old in roots:
            key = hashlib.sha256(str(old.resolve()).encode()).hexdigest()[:16]
            recovery = root / 'Backup' / 'Legacy' / key
            # Keep snapshot filenames usable for the selected database; other
            # locations and conflicts are retained separately, never merged.
            for folder in ('Backup', 'backups'):
                copy_tree(old / folder, root / 'Backup' if old == selected else recovery / folder, recovery / 'Conflicts' / folder)
            if old == selected:
                for folder in ('Catalog', 'Presets', 'Log'):
                    copy_tree(old / folder, root / folder, recovery / 'Conflicts' / folder)
                copy_tree(old / 'Templates', root / 'Presets' / 'Word', recovery / 'Conflicts' / 'Templates')
                manifest = old / 'Root' / 'backup-index.json'
                if safe_file(manifest, old):
                    publish_copy(manifest, runtime / 'backup-index.json')
        if selected is not None and not database_backup(source, database):
            selected = None
        report = {'destination': str(database), 'existing_database_retained': existed, 'database_source': str(source) if selected else None, 'legacy_roots_retained': completed + [str(p.resolve()) for p in roots], 'database_merge': False}
        path = root / 'Log' / 'storage-migration.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        # Diagnostic only; no patient information or credentials.
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        temporary_receipt = runtime / 'storage-migration.tmp'
        temporary_receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
        os.replace(temporary_receipt, receipt)
    finally:
        lock.unlink(missing_ok=True)


def delete_app_data():
    """Explicit uninstall only: fixed PLMS allowlist, no caller-selected path."""
    roots = [data_root(), *legacy_roots()]
    for root in dict.fromkeys(roots):
        if any(linked(parent) for parent in root.parents):
            raise MigrationError('Refusing to follow a linked PLMS data parent: ' + str(root))
        if linked(root):
            # Remove the link itself, never its target (possibly LIS).
            if root.is_symlink():
                root.unlink()
            else:
                os.rmdir(root)
        elif root.is_dir():
            # Python 3.13 on Windows removes junctions without traversing them.
            shutil.rmtree(root)
