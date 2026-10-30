"""Build the real installer document from the immutable approved preview.

No browser libraries, Pillow, network requests or third-party dependencies needed.
The design stylesheet and window markup are copied, not reimplemented in GDI.
"""
from pathlib import Path
import base64
import json
import re

ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'src-tauri/installer/ui'

def build():
    approved=(UI/'approved-preview.html').read_text(encoding='utf-8')
    window=re.search(r'<section class="setup-window"[^>]*>[\s\S]*?</section>',approved).group(0)
    stylesheet=re.search(r'<style>([\s\S]*?)</style>',approved).group(1)
    # Static, embedded assets are present before first paint. No CDN dependencies.
    logo='data:image/svg+xml;base64,'+base64.b64encode((ROOT/'src-tauri/installer/medicsoft-logo.svg').read_bytes()).decode('ascii')
    window=re.sub(r'<img\b',lambda _: '<img src="'+logo+'"',window)
    icons=json.loads((UI/'icons.json').read_text(encoding='utf-8'))
    for name,markup in icons.items():window=window.replace('<i data-lucide="'+name+'"></i>',markup)
    window=window.replace('<span class="window-symbol" aria-hidden="true">−</span>','<button type="button" class="window-symbol" data-chrome="minimize" aria-label="Minimize">−</button>')
    window=window.replace('<span class="window-symbol close-symbol" aria-hidden="true">×</span>','<button type="button" class="window-symbol close-symbol" data-chrome="close" aria-label="Close">×</button>')
    document='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="color-scheme" content="light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Medicsoft PLMS</title><style>'''+stylesheet+'''
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent;color-scheme:light}
#plms-setup-preview{height:100%;line-height:1.625}
#plms-setup-preview .setup-window{position:absolute;left:50%;top:50%;transform-origin:center}
#plms-setup-preview .window-symbol{background:transparent;border:0;border-radius:0;padding:0;color:inherit;flex:0 0 72px;font-family:inherit;cursor:default}
#plms-setup-preview .window-symbol:hover{background:#e5eee8}
#plms-setup-preview .close-symbol:hover{background:#f5dada}
</style></head><body><div id="plms-setup-preview">'''+window+'''</div><script>'''+(UI/'host.js').read_text(encoding='utf-8')+'''</script></body></html>'''
    (UI/'dialog.html').write_text(document,encoding='utf-8')
    print('Built approved installer HTML:',len(document.encode('utf-8')),'bytes')

if __name__=='__main__':build()
