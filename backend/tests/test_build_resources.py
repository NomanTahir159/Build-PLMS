import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import build_resources as builder


class ResourceBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'PLMS project with spaces'
        for relative in ('backend/server.py','backend/Word-Sync.ps1','backend/management.seed.json'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'input')
        self.commands = []

    def tearDown(self):
        self.temp.cleanup()

    def executable(self, name):
        path = self.root / 'backend' / 'dist' / (name + '.exe')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'MZ' + b'\0' * 512)
        return path

    def package(self, command, **options):
        self.assertEqual(options['cwd'], self.root)
        self.assertTrue(options['check'])
        self.commands.append(command)
        self.executable(command[command.index('--name') + 1])

    def build(self, runner=None):
        with patch.object(builder.sys, 'platform', 'win32'), \
             patch.object(builder.importlib.metadata, 'version', return_value=builder.PYINSTALLER_VERSION), \
             patch.object(builder.subprocess, 'run', side_effect=runner or self.package):
            builder.build(self.root)

    def test_clean_build_generates_worker_then_reuses_verified_resource(self):
        self.build()
        self.assertEqual(len(self.commands), 1)
        self.assertIn('--console', self.commands[0])
        self.commands.clear()
        self.build()
        self.assertFalse(self.commands)

    def test_packaging_failure_aborts_instead_of_using_invalid_worker(self):
        invalid = self.executable('plms-backend')
        invalid.write_bytes(b'invalid')
        def fail(command, **options):
            raise subprocess.CalledProcessError(1, command)
        with self.assertRaises(subprocess.CalledProcessError):
            self.build(fail)
        self.assertFalse(invalid.exists())

    def test_success_exit_without_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'valid resource'):
            self.build(lambda *args, **kwargs: None)

    def test_updated_worker_source_triggers_rebuild(self):
        self.executable('plms-backend')
        output = self.executable('plms-backend')
        timestamp = output.stat().st_mtime_ns + 1000000000
        os.utime(self.root / 'backend/server.py', ns=(timestamp, timestamp))
        self.build()
        self.assertEqual(len(self.commands), 1)

    def test_config_hook_and_resources_match(self):
        root = Path(__file__).parents[2]
        config = json.loads((root / 'src-tauri/tauri.conf.json').read_text())
        self.assertEqual(config['build']['beforeBuildCommand'], 'python backend/build_resources.py')
        for name, _, _, _ in builder.artifacts(root):
            self.assertIn('../backend/dist/' + name + '.exe', config['bundle']['resources'])


if __name__ == '__main__':
    unittest.main()
