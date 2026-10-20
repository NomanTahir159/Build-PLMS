"""Build the Windows database resource before Tauri reads its resource configuration.

Called by beforeBuildCommand to ensure the database worker exists before packaging.
"""
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYINSTALLER_VERSION = '6.22.3'


def artifacts(root):
    backend = root / 'backend'
    return [
        ('plms-backend', '--console', backend / 'server.py', [backend / 'server.py', backend / 'Word-Sync.ps1', backend / 'management.seed.json']),
    ]


def valid_executable(path):
    if not path.is_file() or path.stat().st_size < 512:
        return False
    with path.open('rb') as file:
        return file.read(2) == b'MZ'


def needs_build(output, dependencies):
    return not valid_executable(output) or any(dep.stat().st_mtime_ns > output.stat().st_mtime_ns for dep in dependencies)


def build(root=ROOT):
    if sys.platform != 'win32':
        raise RuntimeError('Build PLMS Windows resources on Windows, using GitHub Actions or BUILD-WINDOWS.ps1.')
    from verify import remove_retired_files
    remove_retired_files(root)
    entries = artifacts(root)
    for _, _, _, dependencies in entries:
        for source in dependencies:
            if not source.is_file():
                raise RuntimeError(f'Required build source is missing: {source}')
    try:
        installed = importlib.metadata.version('pyinstaller')
    except importlib.metadata.PackageNotFoundError:
        installed = None
    if installed != PYINSTALLER_VERSION:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                        f'pyinstaller=={PYINSTALLER_VERSION}'], cwd=root, check=True)
    dist = root / 'backend' / 'dist'
    for name, mode, source, dependencies in entries:
        output = dist / (name + '.exe')
        if needs_build(output, dependencies):
            # Remove an invalid/stale executable so a failed build cannot pass validation.
            output.unlink(missing_ok=True)
            command = [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', '--onefile',
                       mode, '--name', name, '--distpath', str(dist),
                       '--workpath', str(root / 'backend' / ('build-' + name)),
                       '--specpath', str(root / 'backend')]
            print(f'Building {name}.exe', flush=True)
            subprocess.run(command + ['--add-data', str(root / 'backend' / 'Word-Sync.ps1') + os.pathsep + '.', '--add-data', str(root / 'backend' / 'management.seed.json') + os.pathsep + '.', str(source)], cwd=root, check=True)
        if not valid_executable(output):
            raise RuntimeError(f'Packaging did not produce a valid resource: {output}')
        print(f'Verified resource: {output.name}', flush=True)


if __name__ == '__main__':
    try:
        build()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f'PLMS resource build failed: {error}', file=sys.stderr)
        sys.exit(1)
