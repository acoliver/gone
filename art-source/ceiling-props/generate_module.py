import importlib.util
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('recipe', ROOT.parent/'ceiling-models/run.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.ROOT = ROOT
for key, name in [('NUMBA_CACHE_DIR','numba'), ('MPLCONFIGDIR','matplotlib'), ('TMPDIR','tmp'), ('XDG_CACHE_HOME','xdg')]:
    r.ENV[key] = str(ROOT/'cache'/name)
for folder in ['logs','cache/numba','cache/matplotlib','cache/tmp','cache/xdg','module']:
    (ROOT/folder).mkdir(parents=True, exist_ok=True)
r.dump(ROOT/'failures.json', [])
shutil.copy2(ROOT.parent/'ceiling-models/render_clay.py', ROOT/'render_clay.py')
source = ROOT.parent/'ceiling-models/refine/beam/seed-210.png'
with Image.open(source) as image:
    w,h=image.size
    image.crop((int(w*.30), int(h*.18), int(w*.72), int(h*.87))).save(ROOT/'module/source-crop.png')
prompt = ROOT/'module/concept.txt'
prompt.write_text('Extract ONE short rectangular armoured light module from this beam grille reference. A standalone shallow cassette approximately 0.60 metres long, 0.18 metres wide and 0.06 metres deep, ratio length to width 3.3. Its own worn olive steel perimeter frame with small rivets and five thin transverse protective louvres over recessed pale frosted light glass. Preserve broad open slots between louvres so the glass remains visible. Remove the structural beam completely. Only one short grille cassette, not a beam or square box. Three-quarter view from below showing the grille face and shallow sides. Entire isolated object on plain neutral grey, no shadows, no room, no text.\n')
concept=ROOT/'module/concept.png'
if not r.flux('module-concept',ROOT/'module/source-crop.png',prompt,concept,220):
    raise RuntimeError('FLUX concept failed')
# The established view recipe accepts descriptive object entries.
text=Path(ROOT.parent/'ceiling-models/run.py').read_text()
start=text.index('def views(chosen):')
end=text.index('\ndef meshes(inputs):',start)
views=text[start:end].replace("'single two-metre ceiling beam segment with its integrated recessed armoured riveted light strip and slotted protective grille on the underside; preserve the integrated strip and its armour'", "'single short shallow rectangular armoured light cassette, 0.60 by 0.18 by 0.06 metres, riveted frame and five thin protective louvres with broad open slots over recessed frosted glass; no structural beam'")
views=views.replace('The long beam lies horizontally; the main visible face is its underside with the grille.', 'The short cassette lies horizontally with length to width 3.3; the main visible face is its underside grille. Preserve the broad open slots.')
exec(views,r.__dict__)
inputs=r.views({'beam':{'path':str(concept)}})
rows=r.meshes(inputs)
if len(rows)!=3:
    raise RuntimeError('Expected three module seeds')
cells=[('Light module concept',concept)]
for row in rows:
    for view in ['front','three-quarter','side']:
        cells.append((f"Module seed {row['seed']} {view}",row['renders'][view]))
r.sheet(cells, ROOT/'module-sheet.jpg', columns=4, tile_w=480, tile_h=360)
r.dump(ROOT/'module-results.json',rows)
(ROOT/'MODULE_READY').touch()
print('MODULE_READY',flush=True)
