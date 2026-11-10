"""Matched perspective views using the demo's wardrobe and doorway cameras."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'her_jacket'))
from render import imported,setup,aim

CAMERAS={
    'wardrobe':{'eye':(4.,1.5,3.05),'target':(7.3,1.17,3.6),'hfov':88.},
    'doorway':{'eye':(4.,1.65,.15),'target':(4.,1.25,6.),'hfov':100.},
}


def native(point):
    x,y,z=point
    return (z-3.6,x-7.675,y)


def render(state,source,out,views):
    scene,camera=setup()
    scene.cycles.samples=24
    scene.render.resolution_x=1920;scene.render.resolution_y=1080
    # Room coordinates are reflected when mapped into ship space.
    scene.use_nodes=True
    nodes=scene.node_tree.nodes;nodes.clear()
    layer=nodes.new('CompositorNodeRLayers')
    flip=nodes.new('CompositorNodeFlip');flip.axis='X'
    composite=nodes.new('CompositorNodeComposite')
    scene.node_tree.links.new(layer.outputs['Image'],flip.inputs['Image'])
    scene.node_tree.links.new(flip.outputs['Image'],composite.inputs['Image'])
    cloth=imported(source)
    furniture=imported(ROOT/'assets/props/quarters/wardrobe.glb')
    tunic=imported(ROOT/f'assets/props/quarters/dress_uniform{"_aged" if state=="aged" else ""}.glb')
    for obj in tunic:
        if obj.parent is None:
            obj.scale.x=-1;obj.location=(0,-.003038027,1.82)
    if state=='aged':
        for obj in tunic:
            if obj.type=='MESH' and obj.name.startswith(('FallenHem','FibreDust','HeapFibres')):
                obj.location.z+=.1445+.95002-1.82
    out.mkdir(parents=True,exist_ok=True)
    camera.data.type='PERSP';camera.data.sensor_fit='HORIZONTAL'
    for name in views:
        if name in CAMERAS:
            pose=CAMERAS[name]
            camera.location=native(pose['eye']);aim(camera,native(pose['target']))
            camera.data.lens=36/(2*math.tan(math.radians(pose['hfov']/2)))
            for obj in furniture+tunic:obj.hide_render=False
        else:
            for obj in furniture+tunic:
                obj.hide_render=not (name=='heap' and obj.name=='BottomPanel')
            if name=='detail':
                camera.location=(-.9,-1.6,.90);aim(camera,(0,-.02,.66));camera.data.lens=48
            elif name=='shoulder':
                camera.location=(-.8,-1.6,1.88);aim(camera,(0,0,1.60));camera.data.lens=60
            elif name=='heap':
                camera.location=(-.6,-1.4,.70);aim(camera,(0,-.05,.15));camera.data.lens=55
        scene.render.filepath=str(out/f'{state}-{name}.png')
        bpy.ops.render.render(write_still=True)
        if state=='aged' and name=='wardrobe':
            for obj in cloth:
                if 'FibreHeap' in obj.name or 'FrayedYarns' in obj.name:obj.hide_render=True
            scene.render.filepath=str(out/'aged-no-fibres-control.png')
            bpy.ops.render.render(write_still=True)
            for obj in cloth:obj.hide_render=False
    (out/'cameras.json').write_text(json.dumps({'room_cameras':CAMERAS,'wardrobe_room_origin':[7.675,0,3.6],
        'wardrobe_room_yaw_deg':-90,'resolution':[1920,1080],'blender_conversion':'(room z-3.6, room x-7.675, room y)',
        'perspective':True,'room_to_ship_reflection':'horizontal compositor reflection, matching the game world handedness',
        'lighting':'unchanged neutral CPU Cycles studio; game lighting requires game captures'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',choices=['remembered','aged'],required=True)
    p.add_argument('--input',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--views',nargs='+',default=['wardrobe','doorway','detail','shoulder','heap'])
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    render(a.state,a.input or ROOT/f'assets/props/quarters/her_dresses{"_aged" if a.state=="aged" else ""}.glb',a.out,a.views)
