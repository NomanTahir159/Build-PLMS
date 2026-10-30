"""Check actual frontend request names against Python and Rust dispatchers."""
import ast
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def string_values(node):
    return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def handled_actions():
    tree = ast.parse((ROOT / 'backend/server.py').read_text(encoding='utf-8'))
    dispatch = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'dispatch')
    actions = set()
    for n in ast.walk(dispatch):
        if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == 'action':
            for comparator in n.comparators:
                actions.update(string_values(comparator))
    # The cloud action group is defined once and dispatched explicitly.
    cloud=ast.parse((ROOT / 'backend/google_drive.py').read_text(encoding='utf-8'))
    actions.update(string_values(next(n.value for n in cloud.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ACTIONS' for t in n.targets))))
    return actions


def requested_actions():
    actions = set()
    sources = [ROOT / 'src/System/index.html', *sorted((ROOT / 'src').glob('**/native*.js')), ROOT / 'src/System/google-drive.js']
    for path in sources:
        source = path.read_text(encoding='utf-8')
        actions.update(re.findall(r"plmsNativeAuth\.call\(\s*['\"]([^'\"]+)['\"]", source))
        if path.name == 'native-backend.js':
            actions.update(re.findall(r"this\.call\(\s*['\"]([^'\"]+)['\"]", source))
            for expression in re.findall(r'raw\(\{action:([^,}]+)', source):
                actions.update(re.findall(r"['\"]([^'\"]+)['\"]", expression))
        if path.name=='google-drive.js':actions.update(re.findall(r"(?:call|run)\(\s*['\"](drive_[a-z_]+)['\"]",source))
        # Include conditional adapter action names.
        for expression in re.findall(r'plmsNativeAuth\.call\(([^,\n]+)', source):
            actions.update(re.findall(r"[?:]\s*['\"]([^'\"]+)['\"]", expression))
    return actions


class NativeActionContractTests(unittest.TestCase):
    def test_every_database_request_has_a_handler(self):
        requested = requested_actions()
        self.assertIn('audit_clear', requested)
        self.assertIn('restore', requested)
        self.assertNotIn('word_updates', requested)
        self.assertNotIn('word_open', requested)
        self.assertFalse(requested - handled_actions(), 'Unhandled native requests: ' + str(requested - handled_actions()))

    def test_all_supported_denials_keep_the_action_name(self):
        tree = ast.parse((ROOT / 'backend/server.py').read_text(encoding='utf-8'))
        handler = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_handle')
        safe_names = set()
        for n in ast.walk(handler):
            if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == 'action':
                for comparator in n.comparators:
                    safe_names.update(string_values(comparator))
        if 'DRIVE_ACTIONS' in (ROOT/'backend/server.py').read_text(encoding='utf-8'):
            from google_drive import ACTIONS
            safe_names.update(ACTIONS)
        self.assertFalse(handled_actions() - safe_names)

    def test_every_direct_tauri_command_is_registered(self):
        rust = (ROOT / 'src-tauri/src/lib.rs').read_text(encoding='utf-8')
        registry = re.search(r'generate_handler!\[([^\]]+)\]', rust).group(1)
        registered = {name.strip().split('::')[-1] for name in registry.split(',')}
        requested = set()
        for path in [ROOT / 'src/System/index.html', *sorted((ROOT / 'src/System').glob('*.js'))]:
            requested.update(re.findall(r"(?:invoke|tauriInvoke)\(\s*['\"]([^'\"]+)['\"]", path.read_text(encoding='utf-8')))
        self.assertIn('plms_backend', requested)
        self.assertFalse(requested - registered, 'Unregistered Tauri commands: ' + str(requested - registered))

    def test_packaged_binary_has_requested_name_and_upgrade_support(self):
        config = json.loads((ROOT / 'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))
        self.assertEqual(config['mainBinaryName'], 'medicsoft-plms')
        source = (ROOT / 'src-tauri/installer/installer.nsi').read_text(encoding='utf-8')
        self.assertIn('ReadRegStr $OldMainBinaryName', source)
        self.assertIn('Delete "$INSTDIR\\$OldMainBinaryName"', source)
        self.assertIn('"$INSTDIR\\$OldMainBinaryName"', source)

