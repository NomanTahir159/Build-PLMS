"""Build and run the x86 WebView2 dialog host used by NSIS."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from build_installer_ui import build as build_ui
from webview2_sdk import prepare

ROOT=Path(__file__).resolve().parents[1]

def compile_native(command,vcvars,output):
    batch=output/'compile-theme.cmd'
    batch.write_text(f'@echo off\ncall "{vcvars}"\nif errorlevel 1 exit /b %errorlevel%\n{command}\nexit /b %errorlevel%\n',encoding='utf-8')
    subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',batch.name],cwd=output,check=True)

def build():
    if sys.platform!='win32':raise RuntimeError('Build the native installer host on Windows with Visual Studio C++ tools.')
    build_ui()
    theme=ROOT/'src-tauri/installer/theme';output=theme/'build';output.mkdir(exist_ok=True)
    sdk=prepare(output/'sdk')
    shutil.copyfile(sdk/'WebView2Loader.dll',output/'WebView2Loader.dll')
    shutil.copyfile(ROOT/'src-tauri/installer/ui/dialog.html',output/'plms-dialog.html')
    vswhere=Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    install=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
    vcvars=Path(install)/'VC/Auxiliary/Build/vcvars32.bat'
    if not vcvars.is_file():raise RuntimeError('Visual Studio x86 C++ build tools are required.')
    dll=output/'plms-theme.dll';smoke=output/'theme-smoke.exe'
    # Static CRT; only Microsoft's x86 WebView2 loader is bundled beside the host.
    libs='user32.lib gdi32.lib comctl32.lib ole32.lib shell32.lib uuid.lib shlwapi.lib'
    options=f'/nologo /std:c++17 /utf-8 /EHsc /W4 /WX /MT /O2 /I"{sdk}"'
    dll.unlink(missing_ok=True)
    compile_native(f'cl {options} /LD "{theme/"plms-theme.cpp"}" /link /DEF:"{theme/"plms-theme.def"}" /OUT:"{dll}" {libs}',vcvars,output)
    compile_native(f'cl {options} "{theme/"smoke.cpp"}" /Fe:"{smoke}" /link {libs}',vcvars,output)
    result=subprocess.run([str(smoke),str(output)],cwd=output)
    if result.returncode==2:
        # The CI runner may lack Evergreen. End-user setup uses its bundled offline installer.
        bootstrap=output/'MicrosoftEdgeWebview2Setup.exe'
        with urllib.request.urlopen('https://go.microsoft.com/fwlink/p/?LinkId=2124703',timeout=90) as response:bootstrap.write_bytes(response.read())
        installed=subprocess.run([str(bootstrap),'/silent','/install'])
        if installed.returncode not in [0,3010]:raise RuntimeError('WebView2 Runtime setup failed')
        subprocess.run([str(smoke),str(output)],cwd=output,check=True)
    elif result.returncode:raise RuntimeError('Native WebView2 integration checks failed.')
    print('Built and tested the approved HTML installer host.')

if __name__=='__main__':build()
