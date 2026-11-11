"""CPU-only neutral studio captures. These are geometry previews, not finished PBR."""
import json
from pathlib import Path
import math

import bpy
from mathutils import Vector

from medal_photoreal import HERE
from medal_stage1_build import material


def studio(out):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'medal-high.blend'))
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=40
    scene.cycles.use_denoising=True
    scene.cycles.seed=130303
    scene.render.threads_mode='FIXED'
    scene.render.threads=10
    scene.render.resolution_x=1200
    scene.render.resolution_y=1200
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='JPEG'
    scene.render.image_settings.quality=94
    scene.view_settings.view_transform='AgX'
    scene.view_settings.exposure=0
    scene.world=bpy.data.worlds.new('NeutralGreyStudio')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.18,.18,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    clay=material('NeutralGreyClay',(.32,.32,.32),0,.42)
    high,low=bpy.data.objects['MedalHigh'],bpy.data.objects['MedalLow']
    raw=bpy.data.objects['ImmutableRegisteredGuide']
    raw.hide_set(False)
    for face in raw.data.polygons:face.use_smooth=True
    objects=[high,low,raw]
    previews={obj.name:list(obj.data.materials) for obj in objects}
    raw.data.materials.clear();raw.data.materials.append(clay)
    for face in raw.data.polygons:face.material_index=0
    lights=[]
    for name,location,power,size in [
        ('SoftKey',(-.048,-.060,.062),.10,.045),
        ('SoftFill',(.055,-.035,.005),.035,.032),
        ('Rim',(.025,.040,.048),.13,.025),
        ('RearSoftbox',(-.04,.055,.020),.045,.035)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=location
        ob.rotation_euler=(Vector((0,0,.002))-ob.location).to_track_quat('-Z','Y').to_euler()
        lights.append(dict(name=name,location=list(location),power_w=power,size_m=size))
    camdata=bpy.data.cameras.new('ReviewCamera');camdata.type='ORTHO';camdata.ortho_scale=.043
    camdata.clip_start=.001;camdata.clip_end=1
    camera=bpy.data.objects.new('ReviewCamera',camdata);scene.collection.objects.link(camera);scene.camera=camera
    angles={
        'front':((0,-.12,.002),(0,0,.002),.043),
        'three-quarter':((-.075,-.12,.052),(0,0,.002),.043),
        'edge-left':((-.12,0,.002),(0,0,.002),.043),
        'rear':((0,.12,.002),(0,0,.002),.043),
        'edge-right':((.12,0,.002),(0,0,.002),.043),
        'three-quarter-right':((.075,-.12,.052),(0,0,.002),.043),
        'attachment':((-.030,-.100,.055),(0,0,.0168),.027),
        'bail-close':((0,-.12,.034),(0,0,.0172),.029),
        'star-centre':((-.018,-.12,.024),(0,0,0),.009),
    }
    frames=[]
    renderdir=out/'renders';renderdir.mkdir(exist_ok=True)
    for obj in objects:
        for candidate in objects:candidate.hide_render=candidate!=obj
        for finish in ['clay','preview'] if obj!=raw else ['clay']:
            if finish=='clay':
                for i in range(len(obj.data.materials)):obj.data.materials[i]=clay
            else:
                for i,mat in enumerate(previews[obj.name]):obj.data.materials[i]=mat
            selected=['front','three-quarter','edge-left','rear']
            if finish=='clay' and obj!=raw:selected+=['edge-right','three-quarter-right','attachment']
            if obj!=raw:selected+=['bail-close','star-centre']
            if obj==raw:selected=['three-quarter']
            for angle in selected:
                location,target,scale=angles[angle]
                if obj==raw:
                    target,scale=(0,0,.006),.057
                camera.location=location
                camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
                camera.data.ortho_scale=scale
                key='raw' if obj==raw else 'high' if obj==high else 'low'
                path=renderdir/f'{key}-{finish}-{angle}.jpg'
                scene.render.filepath=str(path)
                bpy.ops.render.render(write_still=True)
                frames.append(dict(mesh=key,finish=finish,angle=angle,path=str(path),
                                   camera_location=list(location),camera_target=list(target),ortho_scale_m=scale))
                (out/'studio.json').write_text(json.dumps(dict(renderer='Cycles CPU',samples=40,lights=lights,
                                          world_grey_linear=.18,exposure=0,frames=frames),indent=2))
                print('RENDER COMPLETE',path,flush=True)
    print('STUDIO COMPLETE',flush=True)
