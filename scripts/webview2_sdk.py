"""Pinned official Microsoft WebView2 SDK; prepare only build-time headers/loader."""
from pathlib import Path
import hashlib
import re
import urllib.request
import uuid
import zipfile

VERSION='1.0.3485.44'
SHA256='bc09150b179246ac90189649b13be8e6b11b3ac200e817e18df106e1f3cf489e'
URL=f'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/{VERSION}/microsoft.web.webview2.{VERSION}.nupkg'
CALLBACKS=[
 'ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler',
 'ICoreWebView2CreateCoreWebView2ControllerCompletedHandler',
 'ICoreWebView2WebMessageReceivedEventHandler',
 'ICoreWebView2NavigationStartingEventHandler',
 'ICoreWebView2NavigationCompletedEventHandler',
 'ICoreWebView2NewWindowRequestedEventHandler',
 'ICoreWebView2ExecuteScriptCompletedHandler',
 'ICoreWebView2CapturePreviewCompletedHandler',
]

def prepare(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    archive=output/f'webview2-{VERSION}.nupkg'
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:
        with urllib.request.urlopen(URL,timeout=90) as response:payload=response.read()
        if hashlib.sha256(payload).hexdigest()!=SHA256:raise RuntimeError('WebView2 SDK checksum mismatch')
        archive.write_bytes(payload)
    with zipfile.ZipFile(archive) as package:
        header=package.read('build/native/include/WebView2.h')
        (output/'WebView2.h').write_bytes(header)
        (output/'WebView2Loader.dll').write_bytes(package.read('build/native/x86/WebView2Loader.dll'))
        license=next((name for name in package.namelist() if name.lower().endswith('license.txt')),None)
        if license:(output/'WEBVIEW2-LICENSE.txt').write_bytes(package.read(license))
    source=header.decode('utf-8-sig')
    definitions=['#pragma once','template<class T> const GUID& callbackId();']
    for name in CALLBACKS:
        match=re.search(r'MIDL_INTERFACE\("([0-9a-fA-F-]+)"\)\s*'+name+r'\s*:',source)
        if not match:raise RuntimeError('Missing callback ID: '+name)
        value=uuid.UUID(match.group(1));raw=value.bytes
        parts=[str(value.time_low),str(value.time_mid),str(value.time_hi_version)]
        data=','.join(str(x) for x in raw[8:])
        definitions.append('template<> inline const GUID& callbackId<'+name+'>(){ static const GUID value={'+','.join(parts)+',{'+data+'}}; return value; }')
    (output/'webview2-callback-ids.h').write_text('\n'.join(definitions)+'\n',encoding='utf-8')
    return output
