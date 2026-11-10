"""Compose native renders; every component leader uses a ray-verified source projection."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from seat_rail import ROOT, OUT

DEST=ROOT/'tmp/verify-stasis-wiring/seat-rail/readability'
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BG=(22,28,34)
INK=(235,240,244)
ACCENT=(140,224,239)


def font(size=22):
    return ImageFont.truetype(FONT,size)


def text(image,xy,message,size=22,color=INK):
    ImageDraw.Draw(image).text(xy,message,font=font(size),fill=color)


def load(name):
    return Image.open(DEST/(name+'.png')).convert('RGB')


def main():
    manifest=json.loads((DEST/'capture-manifest.json').read_text())
    views={v['name']:v for v in manifest['views']}
    annotations={}
    def paste(image,name,xy):
        raw=load(name)
        image.paste(raw,xy)
    def leader(image,output,name,anchor_id,offset,label_xy,label=None,scale=1.):
        anchor=next(a for a in views[name]['anchors'] if a['id']==anchor_id)
        assert anchor['visible'] and anchor['ray_hit_node']==anchor['node_path']
        p=tuple(anchor['pixel'][i]*scale+offset[i] for i in range(2))
        label=label or anchor_id
        draw=ImageDraw.Draw(image)
        bbox=draw.textbbox(label_xy,label,font=font(20))
        rectangle=(bbox[0]-5,bbox[1]-4,bbox[2]+5,bbox[3]+4)
        end=(min(max(p[0],rectangle[0]),rectangle[2]),min(max(p[1],rectangle[1]),rectangle[3]))
        draw.line([end,p],fill=ACCENT,width=2)
        draw.ellipse([p[0]-3,p[1]-3,p[0]+3,p[1]+3],fill=ACCENT)
        draw.rectangle(rectangle,fill=BG)
        draw.text(label_xy,label,font=font(20),fill=INK)
        annotations.setdefault(output,[]).append({'label':label,'raw_view':name,'source_anchor':anchor_id,
             'source_node':anchor['node_path'],'source':anchor['source'],'pixel':list(p),
             'label_rectangle':list(rectangle),'ray_verified':True})
    def save(image,name):
        assert max(image.size)<=1280
        image.save(DEST/name)

    sheet=Image.new('RGB',(1280,1200),BG)
    text(sheet,(24,12),'One ceiling seat rail, before and after detachment',28)
    text(sheet,(24,47),'Same orthographic camera, 882.76 px/m and fixed neutral inspection lights in all three rows.',18)
    for name,y in [('raw-sheet-full',80),('raw-sheet-gap',320),('raw-sheet-fallen',560)]:
        paste(sheet,name,(0,y))
    text(sheet,(24,88),'Ceiling seat rail | intact 1.20 m source',22)
    text(sheet,(24,328),'Ceiling seat rail | same source, 1.00 m interval removed',22)
    text(sheet,(24,568),'Same part detached | 115 deg roll, real floor-contact pose',22)
    outline=np.asarray(views['raw-sheet-gap']['removed_component_outline_pixels'])+[0,320]
    draw=ImageDraw.Draw(sheet)
    for a,b in zip(outline[:-1],outline[1:]):
        length=np.linalg.norm(b-a)
        for start in np.arange(0,length,12):
            end=min(start+6,length)
            draw.line([tuple(a+(b-a)*start/length),tuple(a+(b-a)*end/length)],fill=ACCENT,width=1)
    text(sheet,(300,520),'Dashed outline: actual removed source projected in its installed position.',17,ACCENT)
    leader(sheet,'shared-component-sheet.png','raw-sheet-gap','left retained end',(0,320),(1030,465))
    leader(sheet,'shared-component-sheet.png','raw-sheet-gap','right retained end',(0,320),(30,465))
    profile=load('raw-profile').resize((300,300),Image.Resampling.LANCZOS)
    sheet.paste(profile,(24,850))
    text(sheet,(24,808),'Actual torn end / C profile (enlarged)',20)
    text(sheet,(356,850),'Source: full.glb / left.glb / middle.glb / right.glb',22)
    text(sheet,(356,890),'36 mm bearing | 42 mm overall | 18 mm deep | 2.5 mm gauge',21)
    text(sheet,(356,930),'Shared source vertices, body triangles and UVs: zero identity error.',20)
    text(sheet,(356,968),'Paired fracture triangles: gap <2e-16 m, opposing normals.',20)
    text(sheet,(356,1006),'No body, texture, profile or lighting changes between these rows.',20)
    text(sheet,(356,1044),'Only the detached piece is rolled; its long axis retains the old rod yaw.',20)
    text(sheet,(356,1082),'The inset is an actual source render, not a drawn replacement section.',19)
    save(sheet,'shared-component-sheet.png')

    installed=Image.new('RGB',(1280,1200),BG)
    text(installed,(24,10),'Installed source and failure | accepted BayCeiling panel context',27)
    paste(installed,'raw-installed-overview',(0,55))
    text(installed,(24,547),'Detail of the same proof: the lower gray formed seat is the detachable component.',22)
    paste(installed,'raw-installed-detail',(0,590))
    leader(installed,'installed-seat-detail.png','raw-installed-detail','ceiling seat rail (intact)',(0,590),(24,615))
    leader(installed,'installed-seat-detail.png','raw-installed-detail','upper support (intact)',(0,590),(940,615))
    leader(installed,'installed-seat-detail.png','raw-installed-detail','same source: left torn end',(0,590),(24,1108))
    leader(installed,'installed-seat-detail.png','raw-installed-detail','same source: right torn end',(0,590),(925,1108))
    text(installed,(24,1171),'Upper support uses BayCeiling._hardware_material(); individual left/right imports use the shared seat PBR.',18)
    save(installed,'installed-seat-detail.png')

    standing=Image.new('RGB',(1280,960),BG)
    text(standing,(24,12),'Standing interaction view | original pickup position, physically rolled C channel',26)
    paste(standing,'raw-standing',(0,60))
    leader(standing,'fallen-stick-standing.png','raw-standing','same part detached',(0,60),(30,820))
    view=views['raw-standing']
    text(standing,(30,864),f"Eye {view['eye_height_m']:.2f} m | pickup plan range {view['pickup_plan_distance_m']:.3f} m | interaction reach 1.30 m",21)
    text(standing,(30,900),'Original bay XZ (-0.60, -1.40) | real 1.00 m piece | 43.69 mm floor height | native floor materials',20)
    save(standing,'fallen-stick-standing.png')

    fracture=Image.new('RGB',(1280,790),BG)
    text(fracture,(24,12),'Matching fracture ends and the actual formed-sheet profile',28)
    text(fracture,(24,53),'Inspection mates are separated 12 mm along their original axis so the shared cut contours can be seen.',20)
    for name,x,title in [('raw-left-mate',0,'Left cut: retained + detached'),('raw-right-mate',430,'Right cut: detached + retained'),('raw-profile',860,'Actual middle end / C section')]:
        text(fracture,(x+12,106),title,21)
        paste(fracture,name,(x,150))
    leader(fracture,'fracture-match-close.png','raw-left-mate','left retained',(0,150),(12,590))
    leader(fracture,'fracture-match-close.png','raw-left-mate','middle left cut',(0,150),(235,627))
    leader(fracture,'fracture-match-close.png','raw-right-mate','right retained',(430,150),(690,590))
    leader(fracture,'fracture-match-close.png','raw-right-mate','middle right cut',(430,150),(442,627))
    leader(fracture,'fracture-match-close.png','raw-profile','actual C profile / torn end',(860,150),(875,590),'Actual C profile / torn end')
    text(fracture,(16,680),'left.glb + middle.glb',20)
    text(fracture,(446,680),'middle.glb + right.glb',20)
    text(fracture,(876,680),'middle.glb, unchanged source',20)
    text(fracture,(24,730),'Both cuts: gap <2e-16 m; opposing normals -1.0. Source IDs and projected triangle anchors are in capture-manifest.json.',18)
    save(fracture,'fracture-match-close.png')

    # Numeric readback and provenance checks do not substitute for image review.
    readbacks={}
    for name in views:
        rgb=np.asarray(load(name),dtype=float)/255.
        lum=rgb.mean(axis=2)
        assert lum.max()-lum.min()>=.015 and lum.var()>=.00001, name+' nonuniform readback'
        assert views[name]['lighting']['lights'],name+' actual inspection lights'
        for material in views[name]['materials']:
            assert material['normal_count']==material['vertex_count']>0,material['node']
            if '/steel_frame' in material['node']:
                assert material['master_hardware_resource'] and material['material_class']=='StandardMaterial3D'
                assert material['albedo_texture'].endswith('/bay-ceiling/materials/intact_albedo.png')
                assert abs(material['metallic']-.62)<1e-6 and abs(material['roughness']-.78)<1e-6
        readbacks[name]={'range':float(np.ptp(lum)),'variance':float(lum.var())}
    old=json.loads((DEST.parent/'capture-manifest.json').read_text())
    for name,sha in old['outputs_sha256'].items():
        assert hashlib.sha256((DEST.parent/name).read_bytes()).hexdigest()==sha,'old proof changed: '+name
    unchanged=[]
    for path,sha in old['source_sha256'].items():
        if '/seat-rail/' in path and (path.endswith('.glb') or path.endswith('.png')):
            assert hashlib.sha256((ROOT/path.removeprefix('res://')).read_bytes()).hexdigest()==sha,path
            unchanged.append(path)
    assert hashlib.sha256((OUT.parent/'stasis-wiring-enclosure.glb').read_bytes()).hexdigest()=='4386c1187f41c7d9a94b7f0dbc9f0e6f5b6f2e715617ff7e9b340a351480e2c5'
    measurements=json.loads((OUT/'manifest.json').read_text())
    manifest.update({'outputs':{name:{'size':list(Image.open(DEST/name).size),'sha256':hashlib.sha256((DEST/name).read_bytes()).hexdigest()} for name in ['shared-component-sheet.png','installed-seat-detail.png','fallen-stick-standing.png','fracture-match-close.png']},
        'annotations':annotations,'readback_checks':readbacks,'measurements':measurements,
        'preserved':{'old_six_pngs':True,'source_meshes_and_pbr':unchanged,'housing_final_sha256':'4386c1187f41c7d9a94b7f0dbc9f0e6f5b6f2e715617ff7e9b340a351480e2c5'},
        'scope':'Static proof only. No ShipScene/main/BayCeiling installation or global light/material changes.'})
    (DEST/'capture-manifest.json').write_text(json.dumps(manifest,indent=2)+chr(10))
    print('READABILITY_COMPOSITION_PASS: four PNGs, projected/ray-verified labels, native PBR and preserved source/old proof checks')


if __name__=='__main__':
    main()
