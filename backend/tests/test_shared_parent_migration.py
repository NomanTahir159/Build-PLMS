import hashlib
from contextlib import closing
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import storage_migration as migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old = self.base / 'Medicsoft PLMS'
        self.new = self.base / 'Medicsoft' / 'PLMS'
        self.path = self.new / 'Database' / 'plms.sqlite3'
        self.sources = []

    def tearDown(self):
        for source in self.sources:
            source.close()
        self.temp.cleanup()

    def db(self, root, value='original', relative='Database/plms.sqlite3'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.executescript('CREATE TABLE records(value); CREATE TABLE credentials(id,hash); CREATE TABLE settings(body);')
        db.execute('INSERT INTO records VALUES(?)', (value,))
        db.execute('INSERT INTO credentials VALUES(?,?)', ('custom-admin', 'existing-password-hash'))
        db.execute('INSERT INTO settings VALUES(?)', (json.dumps({'logo': 'custom', 'catalog': [1, 2], 'session': 60}),))
        db.commit()
        self.sources.append(db)
        return path, db

    def migrate(self, roots=None):
        migration.migrate_storage(self.path, roots or [self.old])

    def test_wal_and_all_tables_survive_without_copying_live_main_file(self):
        old, db = self.db(self.old)
        db.execute('INSERT INTO records VALUES(?)', ('committed-in-wal',))
        db.commit()
        before = old.read_bytes()
        self.assertTrue(Path(str(old) + '-wal').is_file())
        self.migrate()
        self.assertEqual(old.read_bytes(), before)
        with closing(sqlite3.connect(self.path)) as target:
            self.assertEqual(target.execute('SELECT value FROM records').fetchall(), [('original',), ('committed-in-wal',)])
            self.assertEqual(target.execute('SELECT * FROM credentials').fetchall(), [('custom-admin', 'existing-password-hash')])
            self.assertEqual(json.loads(target.execute('SELECT body FROM settings').fetchone()[0])['logo'], 'custom')
            self.assertEqual(target.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.assertTrue(old.exists())

    def test_uncommitted_wal_changes_are_not_migrated(self):
        _, db = self.db(self.old)
        db.execute("INSERT INTO records VALUES('uncommitted')")
        self.migrate()
        with closing(sqlite3.connect(self.path)) as target:
            self.assertEqual(target.execute('SELECT value FROM records').fetchall(), [('original',)])
        db.rollback()

    def test_existing_destination_is_byte_for_byte_untouched(self):
        self.db(self.old)
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'existing file, even if not a usable SQLite database')
        before = self.path.read_bytes()
        self.migrate()
        self.assertEqual(self.path.read_bytes(), before)

    def test_publish_race_does_not_replace_destination(self):
        old, _ = self.db(self.old)
        original = migration.os.link
        def race(source, destination):
            Path(destination).write_bytes(b'raced destination')
            return original(source, destination)
        with patch.object(migration.os, 'link', side_effect=race):
            self.assertFalse(migration.database_backup(old, self.path))
        self.assertEqual(self.path.read_bytes(), b'raced destination')

    def test_multiple_databases_stop_without_selection_or_merge(self):
        self.db(self.old)
        other = self.base / 'older'
        self.db(other, 'other')
        with self.assertRaisesRegex(migration.MigrationError, 'Multiple legacy'):
            self.migrate([self.old, other])
        self.assertFalse(self.path.exists())

    def test_corruption_never_publishes_a_database(self):
        path = self.old / 'Database' / 'plms.sqlite3'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'broken')
        with self.assertRaises(sqlite3.DatabaseError):
            self.migrate()
        self.assertFalse(self.path.exists())
        self.assertEqual(path.read_bytes(), b'broken')
        self.assertFalse(list(self.path.parent.glob('.plms-database-*')))

    def test_old_roaming_location_is_supported(self):
        self.db(self.old, relative='data/plms.sqlite3')
        self.migrate()
        self.assertTrue(self.path.is_file())

    def test_backups_catalog_word_and_logs_retained_with_conflicts(self):
        self.db(self.old)
        for rel in ('Backup/user.json', 'backups/old.json', 'Catalog/catalog.json', 'Presets/Word/template.docx', 'Templates/legacy.docx', 'Log/activity.jsonl', 'Root/backup-index.json'):
            path = self.old / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('original ' + rel)
        (self.new / 'Backup').mkdir(parents=True)
        (self.new / 'Backup' / 'user.json').write_text('destination backup')
        self.migrate()
        self.assertEqual((self.new / 'Backup/user.json').read_text(), 'destination backup')
        self.assertTrue(list((self.new / 'Backup/Legacy').rglob('user.json')))
        self.assertEqual((self.new / 'Catalog/catalog.json').read_text(), 'original Catalog/catalog.json')
        self.assertTrue((self.new / 'Presets/Word/legacy.docx').is_file())
        self.assertTrue((self.new / 'Presets/Word/template.docx').is_file())
        self.assertTrue((self.old / 'Backup/user.json').is_file())
        self.migrate()
        self.assertTrue((self.new / 'Backup/user.json').is_file())

    def test_new_database_and_legacy_backups_remain_separate(self):
        self.db(self.new, 'new')
        self.db(self.old, 'old')
        backup = self.old / 'Backup' / 'snapshot.json'
        backup.parent.mkdir(parents=True)
        backup.write_text('legacy backup')
        self.migrate()
        with closing(sqlite3.connect(self.path)) as target:
            self.assertEqual(target.execute('SELECT value FROM records').fetchone(), ('new',))
        self.assertTrue(list((self.new / 'Backup/Legacy').rglob('snapshot.json')))
        self.assertTrue(backup.exists())

    def test_migration_lock_prevents_parallel_work(self):
        self.db(self.old)
        (self.new / 'Root').mkdir(parents=True)
        (self.new / 'Root/storage-migration.lock').write_text('busy')
        with self.assertRaisesRegex(migration.MigrationError, 'already running'):
            self.migrate()
        self.assertFalse(self.path.exists())

    def test_destination_links_are_not_followed(self):
        self.db(self.old)
        sibling = self.base / 'LIS'
        sibling.mkdir()
        self.new.mkdir(parents=True)
        try:
            (self.new / 'Backup').symlink_to(sibling, target_is_directory=True)
        except OSError:
            self.skipTest('Creating directory symlinks requires permission on Windows.')
        (self.old / 'Backup').mkdir()
        (self.old / 'Backup/test.json').write_text('backup')
        with self.assertRaises(migration.MigrationError):
            self.migrate()
        self.assertEqual(list(sibling.iterdir()), [])

    def test_completed_migration_does_not_resurrect_deleted_backups(self):
        self.db(self.old)
        old=self.old/'Backup/user.json';old.parent.mkdir();old.write_text('backup')
        self.migrate()
        (self.new/'Backup/user.json').unlink()
        self.migrate()
        self.assertFalse((self.new/'Backup/user.json').exists())
        self.assertFalse((self.new/'Backup/Legacy').exists())
        self.assertTrue(old.exists())

    def test_missing_migrated_database_requires_recovery(self):
        self.db(self.old);self.migrate();self.path.unlink()
        with self.assertRaisesRegex(migration.MigrationError,'previously migrated'):
            self.migrate()
        self.assertFalse(self.path.exists())

    def test_backend_startup_migrates_records_credentials_and_settings(self):
        from server import Backend
        from test_backend import fixture, PASSWORD
        old=self.old/'Database/plms.sqlite3'
        api=Backend(old)
        api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':fixture()})
        before=api.load()[1]
        api.db.close()
        with patch.dict(os.environ, {'PROGRAMDATA': str(self.base)}, clear=True):
            migrated=Backend(self.path)
            try:
                result=migrated.handle({'action':'login','username':'admin','password':PASSWORD})
                self.assertEqual(result['state']['patients'],before['patients'])
                self.assertEqual(result['state']['orders'],before['orders'])
                self.assertEqual(result['state']['catalog'],before['catalog'])
                self.assertEqual(migrated.load()[1]['users'],before['users'])
                self.assertTrue(old.exists())
            finally:
                migrated.db.close()

    def test_older_configured_accounts_are_not_reseeded(self):
        from server import Backend
        from test_backend import fixture, PASSWORD
        old=self.old/'Database/plms.sqlite3'
        api=Backend(old)
        api.handle({'action':'bootstrap','username':'admin','password':PASSWORD,'state':fixture()})
        revision,before=api.load()
        before['users'][0]['name']='Custom Lab Administrator'
        api.db.execute('UPDATE app_state SET body=? WHERE id=1',(json.dumps(before),))
        api.db.execute('DELETE FROM local_defaults')
        hashes=api.db.execute('SELECT * FROM credentials').fetchall()
        api.db.close()
        with patch.dict(os.environ, {'PROGRAMDATA':str(self.base)}, clear=True):
            migrated=Backend(self.path)
            try:
                self.assertEqual(migrated.load()[1]['users'],before['users'])
                self.assertEqual(migrated.db.execute('SELECT * FROM credentials').fetchall(),hashes)
                self.assertTrue(migrated.handle({'action':'login','username':'admin','password':PASSWORD})['token'])
            finally:
                migrated.db.close()

    def test_discovery_is_plms_only_and_unset_environment_has_no_relative_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(migration.legacy_roots(), [])
        with patch.dict(os.environ, {'PROGRAMDATA': str(self.base), 'APPDATA': str(self.base / 'roaming'), 'LOCALAPPDATA': str(self.base / 'local')}, clear=True):
            self.assertEqual(migration.data_root(), self.new)
            self.assertTrue(all('LIS' not in str(p) for p in migration.legacy_roots()))
            self.assertIn(self.base / 'roaming/pk.org.sgrh.plms', migration.legacy_roots())

    def test_explicit_delete_preserves_lis_parent_and_unrelated_data(self):
        for root in [self.new, self.base / 'Medicsoft/LIS', self.old, self.base / 'unrelated']:
            root.mkdir(parents=True, exist_ok=True)
            (root / 'keep.txt').write_text('data')
        with patch.dict(os.environ, {'PROGRAMDATA': str(self.base)}, clear=True):
            migration.delete_app_data()
        self.assertFalse(self.new.exists())
        self.assertFalse(self.old.exists())
        self.assertTrue((self.base / 'Medicsoft/LIS/keep.txt').is_file())
        self.assertTrue((self.base / 'unrelated/keep.txt').is_file())
        self.assertTrue((self.base / 'Medicsoft').is_dir())

    def test_explicit_delete_never_follows_nested_lis_link(self):
        lis = self.base / 'Medicsoft/LIS'
        lis.mkdir(parents=True)
        (lis / 'keep.txt').write_text('preserve')
        self.new.mkdir()
        try:
            (self.new / 'linked-lis').symlink_to(lis, target_is_directory=True)
        except OSError:
            self.skipTest('Creating directory symlinks requires permission on Windows.')
        with patch.dict(os.environ, {'PROGRAMDATA': str(self.base)}, clear=True):
            migration.delete_app_data()
        self.assertEqual((lis / 'keep.txt').read_text(), 'preserve')

if __name__ == '__main__':
    unittest.main()
