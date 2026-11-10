"""Sew a woman's jacket and gravity-drape it on the real dining chair."""
import argparse
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cloth_tools import (ASSETS, SCRATCH, collision, cut, deposit, export, fabric,
                         fringe, load_support, mesh, plain, retain_pattern,
                         save_state, solve, weld_seams)


def pattern():
    xs = np.linspace(-.75, .75, 61)
    zs = np.linspace(.275, .900, 26)
    vertices, faces, uv, ids = [], [], [], {}
    for panel in range(2):
        for j in range(25):
            for i in range(60):
                x, z = (xs[i] + xs[i+1])/2, (zs[j]+zs[j+1])/2
                body = abs(x) < .238
                sleeve = .75 < z < .90
                neck = abs(x) < .075 and z > .85
                opening = panel == 0 and abs(x) < .013
                if (not body and not sleeve) or neck or opening:
                    continue
                quad = []
                for ii, jj in ((i,j),(i+1,j),(i+1,j+1),(i,j+1)):
                    key = (panel,ii,jj)
                    if key not in ids:
                        ids[key] = len(vertices)
                        vertices.append((float(xs[ii]), -.10 if panel == 0 else .10, float(zs[jj])))
                        uv.append((float(xs[ii])*8, float(zs[jj])*8))
                    quad.append(ids[key])
                faces.append(tuple(quad) if panel == 0 else tuple(reversed(quad)))
    counts = {}
    for face in faces:
        for a,b in zip(face, face[1:]+face[:1]):
            e=tuple(sorted((a,b)));counts[e]=counts.get(e,0)+1
    boundary={i for e,n in counts.items() if n==1 for i in e}
    pairs=[]
    for (panel,i,j),a in ids.items():
        other=(1,i,j)
        if panel or other not in ids or a not in boundary:
            continue
        b=ids[other]
        x,z=xs[i],zs[j]
        shoulder=z>.895 and abs(x)>.075
        underarm=abs(z-.75)<.001 and abs(x)>.23
        side=abs(abs(x)-.25)<.001 and z<.751
        if shoulder or underarm or side:
            pairs.append((a,b))
    obj=mesh('Jacket',vertices,faces,pairs,uv)
    retain_pattern(obj)
    pins={}
    for (panel,i,j),index in ids.items():
        p=obj.data.vertices[index].co
        s=.90-float(zs[j])
        p.y=s-.10
        p.z=.970 if panel==0 else .950
        p.z+=.002*math.sin(p.x*15+s*10)
        if abs(float(zs[j])-.60)<.001 and .06<abs(xs[i])<.185:
            p.y=.203
            p.z=.9043 if panel==0 else .9013
            pins[index]=1.
    return obj,pairs,pins


def remembered():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    load_support('dining_chair')
    bpy.ops.mesh.primitive_plane_add(size=6)
    floor=bpy.context.object;floor.name='SupportFloor';collision(floor,.0005);floor['support']=True
    obj,pairs,pins=pattern()
    obj.data.materials.append(fabric('SlateWool',(.075,.115,.15),'her_jacket'))
    obj.data.materials.append(fabric('SlateCollarCuffs',(.038,.064,.085),'her_jacket'))
    for face in obj.data.polygons:
        coords=np.array([obj.data.uv_layers.active.data[i].uv[:] for i in face.loop_indices])/8
        x,z=coords.mean(0)
        if abs(x)>.66 or (.72<z<.85 and .025<abs(x)<.10) or (.475<z<.50 and .07<abs(x)<.19):
            face.material_index=1
    record=solve(obj,pins,frames=300,quality=24,time_scale=.25)
    record['seam_gap_before_weld_m']=weld_seams(obj,pairs)
    record['method']='Flat T-cut front and back, open front and neck, shoulder/underarm/side sewing springs; jacket laid across the back with collar toward seat, then gravity-draped on imported dining_chair.glb.'
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH/'jacket-drape.blend'))
    from tailoring import add_tailoring
    add_tailoring(obj)
    record['tailoring']='UV-fitted lapel facings and three dark 8 mm buttons, added to the baked front surface'
    save_state(HERE,'her_jacket','remembered',record)


def aged():
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'her_jacket-remembered.blend'))
    for obj in list(bpy.context.scene.objects):
        if obj.get('aged_export') and obj.name!='Jacket':bpy.data.objects.remove(obj,do_unlink=True)
    for obj in bpy.context.scene.objects:
        if obj.get('support'):collision(obj,.0005)
    obj=bpy.data.objects['Jacket']
    # Tear along a loaded shoulder fold and two lower creases before gravity.
    record={'age_years':1000,'environment':'sealed sterile dry oxygenated; no biology'}
    record['cuts']=cut(obj,lambda p: (.06<p.x<.19 and .79<p.z<.82 and p.y>.21)
                      or (-.19<p.x<-.12 and .36<p.z<.59 and p.y>.22 and abs(p.x+.155+.012*math.sin(p.z*60))<.018)
                      or (.11<p.x<.24 and .29<p.z<.34 and p.y>.20))
    group=obj.vertex_groups['SupportStitches'].index
    pins={v.index:1. for v in obj.data.vertices if v.co.x<.16 and any(g.group==group and g.weight>.99 for g in v.groups)}
    obj.vertex_groups.clear()
    record['gravity_resimulation']=solve(obj,pins,frames=180,sewing=False,aged=True,time_scale=.25)
    obj.data.materials.clear();obj.data.materials.append(fabric('FadedBrittleSlate',(.205,.235,.245),'her_jacket',True))
    obj.data.materials.append(fabric('FadedCollarCuffs',(.17,.20,.21),'her_jacket',True))
    yarn=plain('PaleDryFibres',(.34,.32,.28))
    fringe(obj,yarn,95273,minimum_z=.27,maximum_z=.83,
           blockers=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('support')])
    # The seat height comes from the real 40 mm pad, not the nominal chair spec.
    deposit('SeatFibreDust',(0,-.05,.47245),(.16,.13),yarn,95274,count=95)
    deposit('FloorFibreDust',(.02,.32,.0008),(.29,.13),yarn,95275,count=120)
    from tailoring import add_tailoring
    add_tailoring(obj,aged=True)
    record['tailoring']='Faded lapel facings and three retained buttons fitted to the resimulated surface'
    save_state(HERE,'her_jacket','aged',record)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assemble',action='store_true')
    p.add_argument('--state',choices=['remembered','aged'],default='remembered')
    p.add_argument('--output',type=Path)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if a.assemble:
        remembered() if a.state=='remembered' else aged()
    else:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/f'her_jacket-{a.state}.blend'))
        export(a.output or ASSETS/f'her_jacket{"_aged" if a.state=="aged" else ""}.glb')


if __name__=='__main__':main()
