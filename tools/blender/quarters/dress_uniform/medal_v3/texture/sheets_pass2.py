"""Matched photo / selected tex1 / tex2 sheets, with geometry-only comparisons."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[6]
BEFORE=ROOT/'tmp/issue130-v3/tex1'
FIT2=ROOT/'tmp/issue130-v3/fit2'
OUT=ROOT/'tmp/issue130-v3/tex2'
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',24)
small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
settings=json.loads((OUT/'renders/settings.json').read_text())
rows=settings['renders']
sheets=[]
for state in ['remembered','present']:
    best='A' if state=='remembered' else 'B'
    for view in ['front','oblique']:
        for scale in ['game','close']:
            row=next(r for r in rows if r['state']==state and r['view']==view and r['scale']==scale)
            w,h=row['resolution']
            paths=[BEFORE/'sheets'/f'reference-{state}-{view}-{scale}.png',
                   BEFORE/'renders'/f'{best}-{state}-{view}-{scale}.png',Path(row['path'])]
            sheet=Image.new('RGB',(w*3,h+132),(24,27,31));draw=ImageDraw.Draw(sheet)
            draw.text((16,10),f'{state.capitalize()} | {view} | {scale}: body {round(row["medal_body_width_px"])} px',font=font,fill='white')
            for i,(path,title) in enumerate(zip(paths,['Photo reference',f'tex1 selected route {best}','tex2: corrected rim / state finish'])):
                image=Image.open(path).convert('RGB');assert image.size==(w,h)
                draw.text((i*w+16,48),title,font=font,fill=(222,222,222));sheet.paste(image,(i*w,84))
            draw.text((16,h+96),'Unchanged studio lights/camera method and display scale. Reference registration approximate. No visual assessment.',font=small,fill=(210,210,210))
            path=OUT/'sheets'/f'{state}-{view}-{scale}.png';sheet.save(path)
            sheets.append({'path':str(path),'columns':[str(p) for p in paths],'state':state,'view':view,'scale':scale,'panels_resized':False})
    parts=[Image.open(OUT/'sheets'/f'{state}-{view}-game.png').convert('RGB') for view in ['front','oblique']]
    combined=Image.new('RGB',(parts[0].width,sum(p.height for p in parts)),(24,27,31));y=0
    for image in parts:
        combined.paste(image,(0,y));y+=image.height
    path=OUT/'sheets'/f'{state}-game-front-and-oblique.png';combined.save(path)
    sheets.append({'path':str(path),'state':state,'view':'front-and-oblique','scale':'game','columns':'Photo | tex1 A Remembered / B Present | tex2'})

clay=Image.new('RGB',(3600,1932),(24,27,31));draw=ImageDraw.Draw(clay)
views=['front','three-quarter','star-close','edge']
for row,(folder,title) in enumerate([(FIT2,'fit2 high'),(OUT/'geom','tex2 high')]):
    y=row*966
    for col,view in enumerate(views):
        image=Image.open(folder/f'high-{view}.jpg').convert('RGB');assert image.size==(900,900)
        draw.text((col*900+16,y+16),f'{title} | {view}',font=font,fill='white')
        clay.paste(image,(col*900,y+58))
path=OUT/'sheets/clay-fit2-vs-tex2.png';clay.save(path)
sheets.append({'path':str(path),'rows':['fit2 high','tex2 high'],'columns':views,'panels_resized':False})

textures=json.loads((OUT/'textures.json').read_text())
for state,maps in textures['tex2'].items():
    for name,path in maps.items():
        image=Image.open(path);assert image.size==(2048,2048) and np.isfinite(np.asarray(image)).all(),path
assert len(rows)==8
for row in rows:
    image=Image.open(row['path']);assert image.size==tuple(row['resolution'])
    assert abs(row['medal_body_width_px']-({'game':480,'close':900}[row['scale']]))<.05
verification=json.loads((OUT/'geom/verification.json').read_text())
assert verification['silhouette_pass'] and verification['low_total_triangles']<=10500
manifest={'geometry':{'editable':str(OUT/'geom/medal-fitted.blend'),'high':str(OUT/'geom/medal-high.glb'),'low':str(OUT/'geom/medal-low.glb'),'mapped_low':str(OUT/'geom/medal-low-normalmapped.glb'),
          'decisions':json.loads((OUT/'geom/shape-decisions.json').read_text()),'verification':verification},
          'textures':textures,'texture_decisions':json.loads((OUT/'texture-decisions.json').read_text()),
          'renders':rows,'sheets':sheets,'studio':{'source':'tex1 render_studio.py, identical CPU Cycles 64 samples, AgX contrast, lights/world/cards and camera-registration method. Added enamel-only Principled coat, weight .32 Remembered / .10 Present, coat roughness .09 / .15.'},
          'comparison_selection':{'remembered':'tex1 A colour route selected by driver','present':'tex1 B colour route selected by driver'},
          'normal_diagnostic':json.loads((OUT/'geom/bake-check.json').read_text()),
          'verification':{'textures_2048_and_finite':True,'renders_readable':True,'native_display_widths_px':[480,900],'visual_judgment':False},
          'scope':'Offline medal geometry/material/art scripts and tex2 outputs only. No production/tunic/shader/test changes, commits, installs, downloads, configuration changes or OCR.',
          'limitations':['Reference panels are the existing locally generated photographic-style targets, not physical photographs.','Camera/photo registration remains approximate.','Fine image grain cannot exceed the existing source image resolution.','The 0.075 mm relief rounding is a sampled Gaussian footprint, not a constant-width CAD bevel.','Silhouette gates use the frozen studio and registered game cameras; isolated studio captures are not mounted game captures.', 'Low rim remains a triangle approximation. Profile-deviation measurements in geometry.verification.rim include its remaining angular variation.', 'The normal ray diagnostic reports misses on Body and Loop; see normal_diagnostic. No black core samples were recorded. This is not a clean-reach assertion or a per-texel Cycles audit.']}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'renders-and-sheets.json').write_text(json.dumps({'renders':rows,'sheets':sheets},indent=2))
print('SHEETS_COMPLETE',json.dumps([s['path'] for s in sheets]),flush=True)
