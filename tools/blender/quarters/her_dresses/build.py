"""Sew and settle two civilian dresses in the real wardrobe's free side bays."""
import argparse
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'her_jacket'))
sys.path.insert(0,str(HERE))
import space
import silhouette
import brittle
from cloth_tools import (ASSETS, activate, collision, cut, deposit, export, fabric,
                         fringe, load_support, mesh, plain, retain_pattern,
                         save_state, solve, tube, weld_seams)

RAIL_Y=-.003038027
RAIL_Z=1.82
BAYS=[{'name':'RoseDress','x':-.451,'x_limits':[-.473,-.428],
       'color':(.235,.118,.115),'aged_color':(.34,.275,.25),'hem':.48},
      {'name':'BlueDress','x':.438,'x_limits':[.397,.473],
       'color':(.125,.17,.19),'aged_color':(.27,.30,.30),'hem':.57}]


def hanger(config):
    x=config['x']
    points=[(x,RAIL_Y-.215,1.636),(x,RAIL_Y-.18,1.648),
            (x,RAIL_Y-.10,1.672),(x,RAIL_Y,1.69),
            (x,RAIL_Y+.10,1.672),(x,RAIL_Y+.18,1.648),
            (x,RAIL_Y+.215,1.636),(x,RAIL_Y+.20,1.622),
            (x,RAIL_Y-.20,1.622),(x,RAIL_Y-.215,1.636)]
    obj=tube(config['name']+'_Hanger',points,radius=.0025,sides=8)
    hook_x=x+.026 if x<0 else x
    hook=[(x,RAIL_Y,1.69),(hook_x,RAIL_Y,1.758)]
    # The offset neck clears the left rail socket without moving the dress bay.
    for a in np.linspace(-math.pi/2,math.pi*.80,33):
        hook.append((hook_x,RAIL_Y+.0193*math.cos(a),RAIL_Z+.0193*math.sin(a)))
    neck=tube('Hook',hook,radius=.0025,sides=8)
    activate(obj);neck.select_set(True);bpy.ops.object.join()
    obj.name=config['name']+'_Hanger';obj['aged_export']=True
    obj.data.materials.append(plain('HangerSteel',(.24,.255,.26),.65))
    collision(obj,.0005)
    return obj


def chest_form(config,index):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,
        location=(config['x'],RAIL_Y,1.515))
    obj=bpy.context.object;obj.name=config['name']+'_ChestForm'
    obj.scale=(.010 if index==0 else .015,.167,.13)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.hide_render=True;obj['construction_form']=True
    collision(obj,.0005)


def pattern(config,index):
    nx,nz=20,32
    vertices,faces,uv,grids,pairs,pins=[],[],[],[],[],{}
    hem=config['hem']
    for panel in range(2):
        grid=[]
        for j in range(nz+1):
            t=j/nz
            # The waist and hem remain unsupported, as in the tunic pass.
            width=float(np.interp(t,[0,.60,.72,.86,1],[.238,.143,.167,.185,.24 if index==0 else .20]))
            row=[]
            for i in range(nx+1):
                across=2*i/nx-1
                y=width*across
                top=1.69-.24*abs(y)
                if index==0 and abs(y)>.17:
                    top=1.6492-.9*(abs(y)-.17)
                neck=1.575 if panel==0 else 1.615
                if abs(y)<.08:top=neck+.015*(abs(y)/.08)**2
                z=hem+(top-hem)*t
                x=config['x']+(-.055 if panel==0 else .055)
                row.append(len(vertices));vertices.append((x,y+RAIL_Y,z))
                uv.append((y*8,z*8))
            grid.append(row)
        grids.append(grid)
        for j in range(nz):
            for i in range(nx):
                q=(grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i])
                faces.append(tuple(reversed(q)) if panel==0 else q)
    for j in range(nz+1):
        if j/nz<.83:
            pairs.extend((grids[0][j][i],grids[1][j][i]) for i in (0,nx))
    for i in range(nx+1):
        a,b=grids[0][-1][i],grids[1][-1][i]
        y=vertices[a][1]-RAIL_Y
        if abs(y)>.081:
            pairs.append((a,b))
            # Cap-sleeve tips remain free beyond the hanger's shoulder.
            if abs(y)<.19:
                support_z=float(np.interp(abs(y),[.10,.18,.215],[1.672,1.648,1.636]))
                for k in (a,b):
                    x,yy,z=vertices[k]
                    vertices[k]=(config['x']+(-.0003 if k==a else .0003),yy,support_z+.0033)
                    pins[k]=1.
    obj=mesh(config['name'],vertices,faces,pairs,uv)
    source=retain_pattern(obj)
    for panel,grid in enumerate(grids):
        for row in grid:
            for k in row:source.data.vertices[k].co.x=config['x']+(-.055 if panel==0 else .055)
    for panel,grid in enumerate(grids):
        for j,row in enumerate(grid):
            t=j/nz
            for i,k in enumerate(row):
                p=obj.data.vertices[k].co
                if j==nz and abs(p.y-RAIL_Y)>.081:
                    p.x=config['x']+(-.0003 if panel==0 else .0003)
                    continue
                if k in pins:continue
                center=config['x']
                half=.012 if index==0 else .018
                across=2*i/nx-1
                crown=math.cos(across*math.pi/2)
                depth=.001+crown*(half+.004*math.sin(across*math.pi*4+.4)*math.sin(math.pi*min(1,t/.65)))
                p.x=center+(-depth if panel==0 else depth)
    obj.data.update()
    return obj,pairs,pins


def load_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    load_support('wardrobe')
    space.reserve()
    for index,config in enumerate(BAYS):chest_form(config,index)


def remembered():
    load_scene()
    record={'origin':'wardrobe floor centre, identity transform',
            'rail_native_m':[0,RAIL_Y,RAIL_Z],
            'tunic_source_branch':'issue-114-quarters-demo',
            'tunic_wardrobe_local_hook':[0,1.82,-RAIL_Y],
            'tunic_width_along_rail':True,'bays':BAYS,'dresses':{}}
    for index,config in enumerate(BAYS):
        h=hanger(config)
        obj,pairs,pins=pattern(config,index)
        obj.data.materials.append(fabric(config['name']+'Wool',config['color'],'her_dresses'))
        bpy.context.scene.gravity=(0,0,0)
        sewing=solve(obj,pins,frames=60,collide=False,self_collide=False)
        gap=weld_seams(obj,pairs)
        if gap>.003:raise ValueError(f'{obj.name}: sewing did not close before draping: {gap} m')
        bpy.context.scene.gravity=(0,0,-9.81)
        group=obj.vertex_groups['SupportStitches'].index
        pins={v.index:1. for v in obj.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)}
        result={'sewing_stage':sewing,'seam_gap_before_weld_m':gap,
                'gravity_drape':solve(obj,pins,frames=240,sewing=False,quality=20,time_scale=.25)}
        result['silhouette_fit']=silhouette.fit(obj,RAIL_Y)
        result['collider_fit']=space.fit(obj,index==0)
        result['method']='Flat front/back patterns sewn at sides and shoulders, open neck/armholes, shaped upper chest only as in the tunic pass; waist/hem free, height-dependent union of both tunic envelopes reserved. Chest form is removed before aged resimulation.'
        record['dresses'][config['name']]=result
        # The next solve must not re-evaluate the previous dress's physics.
        for m in list(h.modifiers):h.modifiers.remove(m)
    save_state(HERE,'her_dresses','remembered',record)


def aged():
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'her_dresses-remembered.blend'))
    from dress_finish import restore_inputs
    restore_inputs()
    for obj in list(bpy.context.scene.objects):
        if obj.get('construction_form') or obj.name.endswith('_FinishInput'):
            bpy.data.objects.remove(obj,do_unlink=True)
    for obj in bpy.context.scene.objects:
        if obj.get('support') or obj.get('placement_only') or obj.name.endswith('_Hanger'):
            collision(obj,.0005)
    record={'age_years':1000,'environment':'sealed sterile dry oxygenated; no biology','dresses':{},'bays':BAYS}
    yarn=plain('DryFadedDressFibres',(.39,.35,.30))
    yarn.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.98
    for index,config in enumerate(BAYS):
        obj=bpy.data.objects[config['name']]
        # Release one shoulder's outer load path and break the hem before settling.
        result={'cuts':cut(obj,lambda p: (p.x<config['x'] and 1.59<p.z<1.655 and .105<p.y-RAIL_Y<.14)
                           or p.z<config['hem']+.035+.022*math.sin(p.y*57)+.009*math.sin(p.y*211))}
        group=obj.vertex_groups['SupportStitches'].index
        pins={v.index:1. for v in obj.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)}
        released=[k for k in pins if obj.data.vertices[k].co.y-RAIL_Y>.12]
        for k in released:del pins[k]
        result['released_outer_support_stitches']=len(released)
        if not pins:raise ValueError('Brittle dress must retain a supported shoulder')
        obj.vertex_groups.clear()
        result['gravity_resimulation']=solve(obj,pins,frames=130,sewing=False,aged=True,time_scale=.25)
        result['silhouette_fit']=silhouette.fit(obj,RAIL_Y,aged=True)
        result['collider_fit']=space.fit(obj,index==0)
        obj.data.materials.clear();obj.data.materials.append(fabric(config['name']+'BrittleFaded',config['aged_color'],'her_dresses',True))
        brittle.surface(obj.data.materials[0],config['aged_color'])
        fringe(obj,yarn,95280+index,minimum_z=config['hem']-.2,maximum_z=1.67,
               axis_limit=(-.473,-.23) if index==0 else (.23,.473),
               blockers=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('support') or o.get('placement_only') or o.name.endswith('_Hanger'))])
        deposit(config['name']+'_FibreHeap',(-.39 if index==0 else .39,RAIL_Y,.1448),(.065,.22),yarn,95282+index,count=170,height=.018)
        brittle.heap(config['name']+'_FibreHeap_Base',-.39 if index==0 else .39,RAIL_Y,yarn)
        record['dresses'][config['name']]=result
    save_state(HERE,'her_dresses','aged',record)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assemble',action='store_true')
    p.add_argument('--state',choices=['remembered','aged'],default='remembered')
    p.add_argument('--output',type=Path)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if a.assemble:
        remembered() if a.state=='remembered' else aged()
        from dress_finish import finish
        finish(a.state)
    else:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/f'her_dresses-{a.state}.blend'))
        export(a.output or ASSETS/f'her_dresses{"_aged" if a.state=="aged" else ""}.glb')


if __name__=='__main__':main()
