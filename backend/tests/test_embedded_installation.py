import copy
import json
from pathlib import Path
import tempfile
import unittest
from test_backend import fixture, m
Backend, validate_management = m.Backend, m.validate_management

ROOT = Path(__file__).parents[2]


class EmbeddedInstallationTests(unittest.TestCase):
    def test_current_catalog_and_management_survive_install_edit_restart(self):
        catalog = json.loads((ROOT / 'src/Catalog/catalog.seed.json').read_text(encoding='utf-8'))
        management = json.loads((ROOT / 'backend/management.seed.json').read_text(encoding='utf-8'))
        validate_management(management)
        data = fixture()
        data.update({k: v for k, v in catalog.items() if k != 'version'})
        data['management'] = copy.deepcopy(management)
        data['patients'], data['orders'], data['results'] = [], [], {}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Database/plms.sqlite3'
            api = Backend(path)
            try:
                response = api.handle({'action': 'bootstrap', 'username': 'Noman Tahir', 'password': '123', 'state': data})
                self.assertEqual(response['state']['catalog'], catalog['catalog'])
                self.assertEqual(response['state']['management'], management)
                response['state']['catalog'][0]['range'] = '15 - 30'
                response['state']['management']['employees'][0]['bench'] = 'Updated bench'
                saved = api.handle({'action': 'commit', 'token': response['token'], 'revision': response['revision'], 'state': response['state']})
                api.db.close()
                api = Backend(path)
                reopened = api.handle({'action': 'login', 'username': 'U001', 'password': '123'})
                self.assertEqual(reopened['state']['catalog'], saved['state']['catalog'])
                self.assertEqual(reopened['state']['management'], saved['state']['management'])
                self.assertEqual(reopened['state']['patients'], [])
                self.assertEqual(reopened['state']['orders'], [])
                self.assertEqual(len(reopened['state']['catalog']), 192)
                self.assertEqual(len(reopened['state']['management']['employees']), 61)
                self.assertEqual(json.loads((Path(directory) / 'Catalog/catalog.json').read_text(encoding='utf-8'))['catalog'], saved['state']['catalog'])
            finally:
                api.db.close()
