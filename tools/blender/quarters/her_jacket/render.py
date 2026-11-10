"""CPU Cycles captures of exported clothes, with unchanged furniture and cameras."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ASSETS=ROOT/'assets/props/quarters'


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def imported(path):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o not in before]


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('NeutralStudio');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.60,.60,.60,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.6
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001))
    mat=bpy.data.materials.new('ReviewFloor');mat.diffuse_color=(.32,.32,.30,1)
    bpy.context.object.data.materials.append(mat)
    bpy.context.object.name='ReviewFloor'
    for name,pos,energy in [('Key',(-3,-4,5),500),('Fill',(3,1,4),400),('Rim',(0,4,3),350)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.size=3
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos;aim(obj,(0,0,.8))
    data=bpy.data.cameras.new('ReviewCamera');camera=bpy.data.objects.new('ReviewCamera',data)
    scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
    return scene,camera


def render(prop,state,only=None):
    scene,camera=setup()
    out=ROOT/'docs/art/quarters/sheets'/prop;out.mkdir(parents=True,exist_ok=True)
    cloth=imported(ASSETS/f'{prop}{"_aged" if state=="aged" else ""}.glb')
    furniture=imported(ASSETS/('dining_chair.glb' if prop=='her_jacket' else 'wardrobe.glb'))
    tunic=[]
    if prop=='her_dresses':
        tunic=imported(ASSETS/f'dress_uniform{"_aged" if state=="aged" else ""}.glb')
        for obj in tunic:
            if obj.parent is None:
                obj.scale.x=-1
                obj.location=(0,-.003038027,1.82)
        # The demo moves debris separately onto the wardrobe shelf.
        if state=='aged':
            for obj in tunic:
                if obj.type=='MESH' and obj.name.startswith(('FallenHem','FibreDust','HeapFibres')):
                    obj.location.z+=.1445+.95002-1.82
    if prop=='her_jacket':
        views=[('hero',(1.5,2.4,1.45),(0,.08,.48),1.32),
               ('front',(-1.6,-2.5,1.7),(0,.04,.48),1.32)]
    else:
        views=[('context',(-1.4,-4,2.5),(.08,-.12,1.06),2.65),
               ('shoulder',(-2,-3,2.3),(0,0,1.56),1.30),
               ('heap',(0,-2,.8),(0,0,.155),1.05)]
    for name,pos,target,scale in views:
        if only and name not in only:continue
        if prop=='her_dresses':
            visible=name=='context'
            for obj in furniture+tunic:
                if obj.type=='MESH':obj.hide_render=not (visible or (name=='heap' and obj in furniture and obj.name=='BottomPanel'))
        camera.location=pos;aim(camera,target);camera.data.ortho_scale=scale
        scene.render.filepath=str(out/f'{state}-{name}.png')
        bpy.ops.render.render(write_still=True)
        if state=='aged' and name=='hero':
            for obj in cloth:
                if obj.type=='MESH' and ('FibreDust' in obj.name or 'FibreHeap' in obj.name or 'FrayedYarns' in obj.name):
                    obj.hide_render=True
            scene.render.filepath=str(out/'aged-no-fibres-control.png')
            bpy.ops.render.render(write_still=True)
            for obj in cloth:obj.hide_render=False
    if prop=='her_dresses' and (not only or 'hero' in only):
        for obj in furniture+tunic:
            if obj.type=='MESH':obj.hide_render=True
        bpy.data.objects['ReviewFloor'].location.z=.144
        for name,x in [('RoseDress',-.451),('BlueDress',.438)]:
            for obj in cloth:
                if obj.type=='MESH':obj.hide_render=not obj.name.startswith(name)
            camera.location=(x-3,-1.1,1.8)
            aim(camera,(x,-.003038027,.99));camera.data.ortho_scale=1.90
            tag='rose' if name=='RoseDress' else 'blue'
            scene.render.filepath=str(out/f'{state}-{tag}-broadside.png')
            bpy.ops.render.render(write_still=True)
            if state=='aged':
                for obj in cloth:
                    if obj.type=='MESH' and ('FibreHeap' in obj.name or 'FrayedYarns' in obj.name):obj.hide_render=True
                scene.render.filepath=str(out/f'aged-{tag}-control.png')
                bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prop',choices=['her_jacket','her_dresses'],required=True)
    p.add_argument('--state',choices=['remembered','aged'],required=True)
    p.add_argument('--views',nargs='+')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    render(a.prop,a.state,a.views)
