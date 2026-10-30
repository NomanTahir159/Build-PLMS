"""Rebuild installer assets from the official 512px raster of the supplied SVG.

Optional artwork-authoring dependency: Pillow. Normal package builds use the
checked-in bitmaps and do not need Pillow, Node, or a graphics renderer.
"""
from pathlib import Path
import hashlib
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'src-tauri/installer'
DEEP = '#0f4f38'


def render():
    logo = Image.open(ART / 'official-logo.png').convert('RGBA')
    # Square artwork stays square: no cropping, recoloring, background removal or stretch.
    sidebar = Image.new('RGB', (328, 628), '#edf7f1')
    draw = ImageDraw.Draw(sidebar)
    for y in range(628):
        blend = y / 627
        draw.line((0, y, 328, y), fill=tuple(round(a + (b-a)*blend) for a,b in zip((242,250,246),(226,242,232))))
    # Pale molecular bonds and sample tubes stay behind/below the official logo.
    pale = '#cce7d7'
    for x,y in [(18,425),(80,462),(142,425),(204,462),(266,425),(328,462)]:
        draw.line((x,y,x+62,y+37),fill=pale,width=2)
        draw.line((x,y,x+62,y-37),fill=pale,width=2)
        draw.ellipse((x-5,y-5,x+5,y+5),outline=pale,width=2)
    for x,h in [(100,76),(145,103),(190,65)]:
        draw.rounded_rectangle((x,510-h,x+24,530),radius=10,outline=pale,width=2)
        draw.line((x-2,510-h,x+26,510-h),fill=pale,width=2)
    mark = logo.resize((220,220),Image.Resampling.LANCZOS)
    sidebar.paste(mark,(54,124),mark)
    sidebar.save(ART/'sidebar.bmp')
    sidebar.save(ART/'sidebar-light-preview.png')
    header = Image.new('RGB',(300,114),DEEP)
    mark=logo.resize((90,90),Image.Resampling.LANCZOS)
    header.paste(mark,(198,12),mark)
    header.save(ART/'header-light.bmp')
    header.save(ART/'header-preview.png')
    logo.convert('RGB').save(ART/'brand.bmp')
    logo.save(ART/'medicsoft-installer.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    # One official icon is used by the EXE, setup, uninstaller and shell links.
    icon = (ART/'medicsoft-installer.ico').read_bytes()
    (ROOT/'src-tauri/icons/icon.ico').write_bytes(icon)
    for name, size in [('32x32.png',32),('128x128.png',128),('128x128@2x.png',256),('icon.png',512)]:
        logo.resize((size,size),Image.Resampling.LANCZOS).save(ROOT/'src-tauri/icons'/name)
    resources = ROOT/'src/Resources'
    (resources/'app.ico').write_bytes(icon)
    logo.save(resources/'app.png')
    (resources/'logo.svg').write_bytes((ART/'medicsoft-logo.svg').read_bytes())
    branding=resources/'Branding'
    branding.mkdir(exist_ok=True)
    filename='medicsoft-plms-'+hashlib.sha256(icon).hexdigest()[:12]+'.ico'
    for previous in branding.glob('medicsoft-plms-*.ico'):
        if previous.name!=filename:previous.unlink()
    (branding/filename).write_bytes(icon)
    template=ART/'installer.nsi'
    source=template.read_text(encoding='utf-8')
    pattern=r'(?m)^!define PLMS_SHORTCUT_ICON .*$'
    replacement='!define PLMS_SHORTCUT_ICON "$INSTDIR'+chr(92)+'Resources'+chr(92)+'Branding'+chr(92)+filename+'"'
    source,count=re.subn(pattern,lambda _:replacement,source)
    if count!=1:raise RuntimeError('Expected one shortcut icon definition in installer.nsi')
    template.write_text(source,encoding='utf-8')



if __name__ == '__main__':
    render()
