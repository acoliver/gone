"""Build scale-preserving photo/A/B sheets and the complete local run manifest."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, FIT, OUT, INPUT, REFS, HY, SIZE

font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',24)
small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
textures=json.loads((OUT/'textures.json').read_text())
render_settings=json.loads((OUT/'renders/settings.json').read_text())
projection=json.loads((OUT/'projection/settings.json').read_text())
rows=render_settings['renders']
sheets=[]
reference_panels=[]
for state in ['remembered','present']:
    for view in ['front','oblique']:
        photo_path=REFS[state][view]
        registration=projection['photos'][state][view]
        a,b=registration['axes_px'];theta=registration['rotation_radians']
        radius=projection['mesh_enamel_radius_m']
        # Scale the photographed blue-field ellipse by the unchanged body's
        # measured width/rim radius. Panels retain requested display pixels.
        xradius=np.sqrt((a*np.cos(theta))**2+(b*np.sin(theta))**2)
        body_width_photo=2*xradius*(.031765007/2)/radius
        for scale in ['game','close']:
            matched=[next(r for r in rows if r['route']==route and r['state']==state and r['view']==view and r['scale']==scale) for route in ['A','B']]
            row=matched[0];w,h=row['resolution'];bbox=row['body_bbox_px']
            photo=Image.open(photo_path).convert('RGB')
            factor=row['medal_body_width_px']/body_width_photo
            resized=photo.resize((round(photo.width*factor),round(photo.height*factor)),Image.Resampling.LANCZOS)
            center=registration['center_px']
            x=(bbox[0]+bbox[2])/2-center[0]*factor
            y=(bbox[1]+bbox[3])/2-center[1]*factor
            panel=Image.new('RGB',(w,h),(38,41,46));panel.paste(resized,(round(x),round(y)))
            panel_path=OUT/'sheets'/f'reference-{state}-{view}-{scale}.png';panel.save(panel_path)
            reference_panels.append({'path':str(panel_path),'source':str(photo_path),'resize_factor':factor,
                'source_estimated_body_width_px':body_width_photo,'body_width_px':row['medal_body_width_px'],
                'method':'Crop/resize to approximate matching body scale and center. No relighting or colour changes. Original garment/ribbon remain in reference only.'})
            sheet=Image.new('RGB',(w*3,h+132),(24,27,31));draw=ImageDraw.Draw(sheet)
            title=f'{state.capitalize()} | {view} | {scale}: medal body {round(row["medal_body_width_px"])} px across'
            draw.text((16,10),title,font=font,fill='white')
            for i,text in enumerate(['Photo reference','Route A: Hunyuan Paint + Delight','Route B: delit photo projection']):
                draw.text((i*w+16,48),text,font=font,fill=(222,222,222))
            for i,image in enumerate([panel]+[Image.open(r['path']).convert('RGB') for r in matched]):
                sheet.paste(image,(i*w,84))
            draw.text((16,h+96),'Neutral studio for A/B; reference includes wool/ribbon. Approximate camera registration. No visual rating performed.',font=small,fill=(210,210,210))
            path=OUT/'sheets'/f'{state}-{view}-{scale}.png';sheet.save(path)
            sheets.append({'state':state,'view':view,'scale':scale,'path':str(path),
                           'columns':[str(panel_path),matched[0]['path'],matched[1]['path']],
                           'size':list(sheet.size),'render_panels_resized':False})
for state in ['remembered','present']:
    images=[Image.open(next(s['path'] for s in sheets if s['state']==state and s['view']==view and s['scale']=='game')).convert('RGB') for view in ['front','oblique']]
    sheet=Image.new('RGB',(images[0].width,sum(i.height for i in images)),(24,27,31));y=0
    for image in images:
        sheet.paste(image,(0,y));y+=image.height
    path=OUT/'sheets'/f'{state}-game-front-and-oblique.png';sheet.save(path)
    sheets.append({'state':state,'view':'front-and-oblique','scale':'game','path':str(path),'size':list(sheet.size),
                   'order':'Front above oblique; photo reference | A | B in each row','render_panels_resized':False})

source_manifest=json.loads((ROOT/'tmp/issue130-regen2/manifest.json').read_text())
reference_manifest=json.loads((ROOT/'tmp/issue130-reference/photo-20261111-01/manifest.json').read_text())
reference_records=[]
for views in REFS.values():
    for path in views.values():
        selected=next(r for r in reference_manifest['records'] if r.get('seed')==int(path.stem.split('seed')[-1]) and r.get('state','').lower()==path.stem.split('-')[0] and r.get('angle')==path.stem.split('-')[1])
        reference_records.append({'path':str(path),'generation':selected,'metadata':json.loads(path.with_suffix('.metadata.json').read_text())})
geometry_inputs=[str(FIT/name) for name in ['medal-high.glb','medal-low.glb','medal-low-normalmapped.glb','medal-low-normal.png','medal-fitted.blend','low-arrays.json','features.json','normal-bake.json','bake-check.json']]
manifest={
    'task':'gone #130, fitted generated medal image-derived material comparison',
    'output_root':str(OUT),'source_root':str(Path(__file__).resolve().parent),
    'geometry_unchanged':True,'geometry_inputs':geometry_inputs,
    'image_condition':next(i for i in source_manifest['inputs'] if i['path']==str(INPUT)),
    'photographic_style_reference_inputs':reference_records,
    'reference_selection':str(ROOT/'tmp/issue130-reference/reference-selection.md'),
    'methodology':str(ROOT/'tmp/followup/methodology-assessment.md'),
    'installed_code_inputs':[str(HY/x) for x in ['paint.py','mlx_hunyuan3d/paint_pipeline.py','mlx_hunyuan3d/paint_conditioning.py','mlx_hunyuan3d/paint_scheduler.py','mlx_hunyuan3d/paint_weights.py','mlx_hunyuan3d/delight.py','mlx_hunyuan3d/texture_bake.py','mlx_hunyuan3d/rasterizer.py']],
    'paint':json.loads((OUT/'paint/settings.json').read_text()),
    'bake':json.loads((OUT/'bakes/settings.json').read_text()),
    'projection':projection,'rendering':render_settings,
    'material_derivation':{
        'working_colour_space':'Linear RGB, using standard piecewise sRGB transfer; outputs basecolor sRGB, scalar maps and normal Non-Color.',
        'paint_colour_control':'Exact triangle/barycentric transfer from generated atlas. Per-material per-channel median matched to corresponding photographic state; Paint supplies spatial variation. No paint mesh is shipped.',
        'photo_segmentation':'Blue: b>1.7r, b>1.22g, b>.10. Whole isolated components >500 px with bbox inside x .30-.72, y .35-.90 of frame. Remove components below .12 of largest retained area. Brass: r>1.2b, g>1.05b, r>.95g within radius 1.35 of enamel ellipse.',
        'photo_delight':'For each material, divide linear RGB by mask-normalized Gaussian luminance with sigma .14*max(diag(ellipse matrix)), then multiply median masked luminance. Luminance coefficients .2126/.7152/.0722. Minimum divisor .004.',
        'image_variation':'d=clamp((linear luminance - material median)/(material p90-p10),-1,1); minimum range .005.',
        'mask_variables':'e=enamel ID; b=1-e; w=convex; c=clamp(.65*concave+.6*(1-AO),0,1).',
        'remembered':{
            'basecolor':'image colour*(1-.08*c*b)',
            'roughness':'(.29-.07*w+.06*c-.045*d)*b + (.15-.025*d)*e; clamp .08-.8',
            'metallic':'.98*b','oxide_mask':'0','dust_mask':'0',
        },
        'present':{
            'age_years':1000,
            'oxide_mask':'o=clamp((.22+.62*c-.23*w-.12*d)*b,0,.82)',
            'dust_mask':'t=clamp((.10*c+.045*max(-d,0))*(1-.7*w),0,.18)',
            'oxide_colour':'median projected present RGB at brass texels with d<0',
            'dust_colour':'85th percentile projected present enamel RGB',
            'basecolor':'q=image*(1-.22*o); q=q*(1-.20*o)+oxide_colour*.20*o; result=q*(1-t)+dust_colour*t',
            'roughness':'(.43+.18*o+.08*c-.065*w-.035*d)*b + (.22+.22*t-.02*d)*e; clamp .08-.8',
            'metallic':'clamp(.94-.54*o-.55*t,0,1)*b',
            'intent':'Dry brown oxide concentrated in recesses, dull metallic high points, intact slightly dulled enamel and fine image-derived variation; no green corrosion, no wet streaks.',
        },
        'packing':'ORM=AO,roughness,metallic. Nearest covered-texel dilation outside UV islands; no random noise.',
    },
    'textures':textures,'shared_textures':{p.stem:str(p) for p in sorted((OUT/'bakes').glob('*.png'))},
    'intermediate_colour_paths':sorted(str(p) for folder in ['paint','projection'] for p in (OUT/folder).glob('*.png')),
    'editable_studios':[str(OUT/route/state/'studio.blend') for route in textures for state in textures[route]],
    'reference_panels':reference_panels,'sheets':sheets,
    'visual_judgment':'Not performed, as instructed. No image reviewer, OCR or visual scoring.',
    'limitations':[
        'Reference images are preselected locally generated photographic-style targets, not newly captured physical samples.',
        'Smooth-luminance division and neural Delight estimate albedo. They cannot exactly separate metal reflection from pigment.',
        'Paint resolution is 512 per view. Resampling to 2048 UVs adds no source detail.',
        'No back reference supplied. Hidden backs/hardware continue the nearest observed brass colour.',
        'Photo pose/scale registration is an approximate blue-field ellipse fit. Geometries and photographic contexts differ.',
        'Close-up reference panels are enlarged from the supplied images; renders retain their native requested display scale.',
        'Isolated studio renders only. No production integration, tunic, game shader, tests or source geometry changes.',
    ],
    'execution':{'offline':True,'installs':False,'downloads':False,'commits':False,
        'long_jobs':'nohup, workspace-local logs, polling; Paint finished before Blender jobs; no other process killed.',
        'logs':[str(OUT/x) for x in ['paint.log','bake.log','bake-run2.log','colours.log','render.log']],
        'corrected_run_failure':'Initial bake stopped before AO because the low bake target remained render-disabled after the geometry pass. Explicit per-pass target visibility fixed it; completed bake-run2 replaced the maps.',
        'image_registration_correction':'Initial hue mask included wool/ribbon. Whole-component isolation removed those components before colour projection.'},
}
# Engineering validation only: readable finite textures, exact normal reuse,
# complete render count and explicit measured display widths.
occupied=np.load(OUT/'bakes/uv-surface.npz')['occupied']
idmap=np.asarray(Image.open(OUT/'bakes/enamel-id.png'),float)/255
assert np.any(idmap[occupied]>.9) and np.any(idmap[occupied]<.1)
for route,states in textures.items():
    for state,maps in states.items():
        for name,path in maps.items():
            image=Image.open(path)
            assert image.size==(SIZE,SIZE),(path,image.size)
            pixels=np.asarray(image)
            assert np.isfinite(pixels).all(),path
assert (OUT/'bakes/normal.png').read_bytes()==(FIT/'medal-low-normal.png').read_bytes()
assert len(rows)==16,len(rows)
for row in rows:
    assert Path(row['path']).is_file()
    assert abs(row['medal_body_width_px']-({'game':480,'close':900}[row['scale']]))<.05,row
manifest['verification']={'texture_dimensions':[SIZE,SIZE],'finite_texture_pixels':True,
    'normal_byte_identical_to_fit2':True,'two_material_id_classes_present':True,
    'paint_transfer_max_vertex_distance_m':projection['atlas_transfer_max_vertex_distance_m'],
    'render_count':len(rows),'sheet_count':len(sheets),
    'measured_body_widths_px':sorted(set(round(row['medal_body_width_px'],3) for row in rows)),
    'visual_assessment':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'renders-and-sheets.json').write_text(json.dumps({'renders':rows,'sheets':sheets},indent=2))
print('MANIFEST_COMPLETE',str(OUT/'manifest.json'),flush=True)
print('SHEETS',json.dumps([s['path'] for s in sheets]),flush=True)
