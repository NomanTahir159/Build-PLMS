"""Exercise audit clearing on a temporary database, including authorization."""
import copy
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from test_backend import fixture, PASSWORD
from server import Backend, ApiError


class AuditClearTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / 'Database/plms.sqlite3'
        self.api = Backend(self.path)
        self.auth = self.api.handle({'action': 'bootstrap', 'username': 'admin', 'password': PASSWORD, 'state': fixture()})
        self.log = self.path.parent.parent / 'Log/activity.jsonl'

    def tearDown(self):
        self.api.db.close()
        self.tmp.cleanup()

    def call(self, action, **extra):
        return self.api.handle({'action': action, 'token': self.auth['token'], **extra})

    def test_clear_is_persistent_and_preserves_other_records(self):
        snapshot = self.call('snapshot_create', reason='On demand')['row']
        before = copy.deepcopy(self.call('read'))
        credentials = list(self.api.db.execute('SELECT * FROM credentials'))
        self.assertTrue(self.log.read_text())
        self.assertGreater(self.call('audit_clear')['removed'], 0)
        self.assertEqual(self.call('audit')['events'], [])
        self.assertEqual(self.log.read_text(), '')
        self.assertEqual(self.call('audit_clear')['removed'], 0)
        self.assertEqual(self.call('read'), before)
        self.assertEqual(list(self.api.db.execute('SELECT * FROM credentials')), credentials)
        self.assertEqual(self.call('snapshot_read', id=snapshot['id'])['row']['id'], snapshot['id'])
        self.api.db.close()
        self.api = Backend(self.path)
        self.assertEqual(self.api.db.execute('SELECT COUNT(*) FROM security_audit').fetchone()[0], 0)
        self.api.handle({'action': 'login', 'username': 'admin', 'password': PASSWORD})
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['action'], 'Signed in')

    def test_missing_or_forged_session_cannot_clear(self):
        original = list(self.api.db.execute('SELECT id FROM security_audit'))
        for token in (None, 'forged'):
            with self.assertRaises(ApiError):
                self.api.handle({'action': 'audit_clear', 'token': token})
        for row in original:
            self.assertIsNotNone(self.api.db.execute('SELECT id FROM security_audit WHERE id=?', row).fetchone())

    def test_delete_permission_is_required_and_can_be_granted(self):
        current = self.call('read')
        current['state']['users'].append({'id': 'viewer', 'name': 'Viewer', 'role': 'Viewer', 'status': 'Active', 'department': 'All', '__nativePassword': PASSWORD})
        current['state']['rolePermissions']['Viewer']['audit.view'] = True
        self.call('commit', state=current['state'], revision=current['revision'])
        viewer = self.api.handle({'action': 'login', 'username': 'viewer', 'password': PASSWORD})
        with self.assertRaisesRegex(ApiError, 'audit.delete'):
            self.api.handle({'action': 'audit_clear', 'token': viewer['token']})
        self.assertTrue(self.call('audit')['events'])
        current = self.call('read')
        current['state']['userPermissionOverrides']['viewer'] = {'audit.delete': True}
        self.call('commit', state=current['state'], revision=current['revision'])
        self.api.handle({'action': 'audit_clear', 'token': viewer['token']})
        self.assertEqual(self.call('audit')['events'], [])

    def test_log_write_failure_rolls_back_database_clear(self):
        original = list(self.api.db.execute('SELECT id FROM security_audit'))
        with patch('server.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaisesRegex(ApiError, 'could not be cleared'):
                self.call('audit_clear')
        self.assertFalse(self.api.db.in_transaction)
        for row in original:
            self.assertIsNotNone(self.api.db.execute('SELECT id FROM security_audit WHERE id=?', row).fetchone())
