#!/usr/bin/env python3
from pathlib import Path
import hashlib,re,sys
from fontTools import subset
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'demo-v2'
chars=''.join(p.read_text() for p in folder.glob('*') if p.suffix in ['.html','.js','.css'])
chars+=''.join(p.read_text() for p in (ROOT/'android/app/src/main/java').rglob('*.kt'))
chars+=''.join(chr(x) for x in range(32,127))
o=subset.Options();o.flavor='woff2';o.hinting=False;f=subset.load_font(str(ROOT/'android/app/src/main/res/font/pretendard.ttf'),o)
s=subset.Subsetter(options=o);s.populate(text=chars);s.subset(f);subset.save_font(f,str(folder/'font.woff2'),o)
font_hash=hashlib.sha256((folder/'font.woff2').read_bytes()).hexdigest()[:12]
css=(folder/'style.css').read_text();css=re.sub(r"/font\.woff2(?:\?v=[a-f0-9]+)?",'/font.woff2?v='+font_hash,css);(folder/'style.css').write_text(css)
worklet_hash=hashlib.sha256((folder/'audio-worklet.js').read_bytes()).hexdigest()[:12]
js=(folder/'app.js').read_text();js=re.sub(r"/audio-worklet\.js\?v=[a-zA-Z0-9-]+",'/audio-worklet.js?v='+worklet_hash,js);(folder/'app.js').write_text(js)
html=(folder/'index.html').read_text()
for name in ['app.js','style.css']:
 digest=hashlib.sha256((folder/name).read_bytes()).hexdigest()[:12]
 html=re.sub('/'+re.escape(name)+r'\?v=[^"\s]+','/'+name+'?v='+digest,html)
preview=folder/'preview.mp4'
if preview.exists():html=re.sub(r'/preview\.mp4(?:\?v=[a-f0-9]+)?','/preview.mp4?v='+hashlib.sha256(preview.read_bytes()).hexdigest()[:12],html)
(folder/'index.html').write_text(html)
family=(folder/'family.html').read_text();family=re.sub(r'/style\.css(?:\?v=[a-f0-9]+)?','/style.css?v='+hashlib.sha256((folder/'style.css').read_bytes()).hexdigest()[:12],family);(folder/'family.html').write_text(family)
print('Portal assets:',(folder/'font.woff2').stat().st_size,'byte font; script/style cache versions updated')

if '--publish'in sys.argv:
 from delivery_assets import publish_portal
 print(publish_portal())
