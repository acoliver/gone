import sys, json
from pathlib import Path
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
source=OUT.parents[1]/'kbmodel/build_keyboard.py'
# Run only layout capture and its explicit control-footprint corrections.
text=source.read_text();prefix=text[text.index('class Capture:'):text.index('# --factory-startup')]
sys.path.insert(0,str(OUT.parents[1]/'terminal'))
import build_deliverables as layout
import build_icons as icons
ns={'layout':layout};exec(prefix,ns)
keys=[]
for i,(rect,(group,name)) in enumerate(zip(ns['capture'].rects,ns['labels'])):
 paths=layout.ONSETS[name] if group=='onset' else layout.VOWELS[name] if group=='vowel' else None
 keys.append({'index':i+1,'group':group,'name':name,'rect':rect,'paths':paths})
(OUT/'design.json').write_text(json.dumps(keys,indent=2))
print([(k['index'],k['name'],[(k['rect'][0]+k['rect'][2])/2,(k['rect'][1]+k['rect'][3])/2]) for k in keys])
