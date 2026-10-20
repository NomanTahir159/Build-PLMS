"""Remove specifically retired source files before discovering current tests."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RETIRED = ('backend/account_setup.py', 'backend/tests/test_installer_account.py')


def remove_retired_files(root=ROOT):
    for relative in RETIRED:
        path = root / relative
        if path.is_file():
            path.unlink()
            print(f'Removed retired source: {relative}', flush=True)


if __name__ == '__main__':
    remove_retired_files()
    sys.exit(subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                            '-s', 'backend/tests', '-v'], cwd=ROOT).returncode)
