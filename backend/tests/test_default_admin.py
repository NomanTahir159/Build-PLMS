import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from server import Backend, ApiError, password_hash, password_verify
from test_backend import fixture


class DefaultAdministratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'plms.sqlite3'
        self.api = Backend(self.path)

    def tearDown(self):
        self.api.db.close()
        self.temp.cleanup()

    def test_fresh_default_credentials_and_exact_display_name(self):
        auth = self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
        self.assertEqual(auth['userId'], 'U001')
        user = next(u for u in auth['state']['users'] if u['id']=='U001')
        self.assertEqual((user['name'],user['role'],user['status']), ('Noman Tahir','Administrator','Active'))
        stored = self.api.db.execute("SELECT hash FROM credentials WHERE id='U001'").fetchone()[0]
        self.assertNotEqual(stored, '123')
        self.assertTrue(password_verify('123', stored))
        reopened = Backend(self.path)
        try:
            self.assertTrue(reopened.handle({'action':'login','username':'U001','password':'123'})['token'])
        finally:
            reopened.db.close()

    def test_existing_database_gets_default_without_losing_records(self):
        self.api.handle({'action':'bootstrap','username':'old-admin','password':'An existing strong password','state':fixture()})
        # Represents an installation from before the one-time default marker existed.
        self.api.db.execute('DELETE FROM local_defaults')
        before = self.api.db.execute('SELECT body FROM app_state').fetchone()[0]
        reopened = Backend(self.path)
        try:
            auth = reopened.handle({'action':'login','username':'U001','password':'123'})
            self.assertEqual(auth['state']['patients'], json.loads(before)['patients'])
            self.assertEqual(auth['state']['orders'], json.loads(before)['orders'])
            self.assertTrue(reopened.handle({'action':'login','username':'old-admin','password':'An existing strong password'})['token'])
        finally:
            reopened.db.close()

    def test_password_change_survives_reopening_without_reset(self):
        auth = self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
        self.api.handle({'action':'password','token':auth['token'],'current':'123','password':'My changed strong password'})
        reopened = Backend(self.path)
        try:
            with self.assertRaises(ApiError):
                reopened.handle({'action':'login','username':'U001','password':'123'})
            self.assertTrue(reopened.handle({'action':'login','username':'U001','password':'My changed strong password'})['token'])
        finally:
            reopened.db.close()

    def test_existing_misspelling_corrected_without_password_reset(self):
        auth=self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
        self.api.handle({'action':'password','token':auth['token'],'current':'123','password':'My changed strong password'})
        revision,state=self.api.load()
        next(u for u in state['users'] if u['id']=='U001')['name']='Noman Thair'
        self.api.db.execute('UPDATE app_state SET body=? WHERE id=1',(json.dumps(state),))
        self.api.db.execute("DELETE FROM local_defaults WHERE key='default_admin_name_v2'")
        stored=self.api.db.execute("SELECT hash FROM credentials WHERE id='U001'").fetchone()[0]
        reopened=Backend(self.path)
        try:
            result=reopened.handle({'action':'login','username':'U001','password':'My changed strong password'})
            self.assertEqual(next(u for u in result['state']['users'] if u['id']=='U001')['name'],'Noman Tahir')
            self.assertEqual(reopened.db.execute("SELECT hash FROM credentials WHERE id='U001'").fetchone()[0],stored)
        finally:reopened.db.close()

    def test_custom_name_survives_spelling_migration(self):
        self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
        revision,state=self.api.load()
        next(u for u in state['users'] if u['id']=='U001')['name']='Custom Administrator'
        self.api.db.execute('UPDATE app_state SET body=? WHERE id=1',(json.dumps(state),))
        self.api.db.execute("DELETE FROM local_defaults WHERE key='default_admin_name_v2'")
        reopened=Backend(self.path)
        try:self.assertEqual(next(u for u in reopened.load()[1]['users'] if u['id']=='U001')['name'],'Custom Administrator')
        finally:reopened.db.close()

    def test_default_account_survives_backup_restore(self):
        auth=self.api.handle({'action':'bootstrap','username':'U001','password':'123','state':fixture()})
        state=self.api.handle({'action':'backup','token':auth['token']})['state']
        self.api.handle({'action':'restore','token':auth['token'],'state':state})
        self.assertTrue(self.api.handle({'action':'login','username':'U001','password':'123'})['token'])

    def test_short_password_exception_is_limited_to_requested_default(self):
        with self.assertRaises(ApiError):
            password_hash('123')
        with self.assertRaises(ApiError):
            self.api.handle({'action':'bootstrap','username':'other','password':'123','state':fixture()})
        self.assertFalse(self.api.initialized())


if __name__=='__main__':
    unittest.main()
