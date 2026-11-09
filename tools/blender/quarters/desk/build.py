"""Fair the approved generated desk into a worktop, pedestal and drawer trays."""
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import aim, attach, build_main, cylinder, empty, materials, panel, recess, rivets

SPEC={
    'bounds_gltf':[[-.8,0,-.35],[.8,.76,.35]],
    'required_nodes':['Desk','Body','Worktop','Drawers','Drawer_0','Drawer_1','Drawer_2','EndSupport','EndPanel','PedestalKick','RearUpstand','ModestyPanel'],
    'parents':{'Body':'Desk','Drawers':'Desk','Worktop':'Body',
               **{f'Drawer_{i}':'Drawers' for i in range(3)}},
    'pivots_gltf':{'Desk':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel'],
    'visible_details':['DrawerPull_1','WorktopRivets','PedestalKick','ModestyPanel'],
    'hero_camera_native':[-.8,-5,1.8],'hero_camera_gltf':[-.8,1.8,5],
    'hero_target_native':[0,0,.38],'triangle_limit':15000,
    'drawer_motion_axis_gltf':[0,0,1],
    'fit_notes':'The generated left pedestal inner wall sets drawer width. Seed 227 has a thin solid right end panel. Guide edge samples reach .76 m while the central worktop reaches .705 m. The fitted top is .70 m; the rear lip remains 60 mm and side returns are reduced to 20 mm to follow the flatter approved image. The kick face and rear plate have capture-matched first-hit gates. A studio-only low fill reveals the plate beneath the overhanging top; it is not exported. Each drawer is a separate open-top five-panel tray under its own slide origin.',
}


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    shader=dark.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=(.010,.014,.014,1)
    shader.inputs['Metallic'].default_value=.05
    bare.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.45,.48,.49,1)
    bare.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.35
    root=empty('Desk'); body=empty('Body',parent=root); drawers=empty('Drawers',parent=root)
    points=np.array([list(v.co) for obj in bpy.data.objects if obj.name.startswith('Guide_')
                     for v in obj.data.vertices])
    sample=points[(points[:,0]<-.2)&(points[:,2]>.12)&(points[:,2]<.65)&(np.abs(points[:,1])<.25)]
    measured=float(np.quantile(sample[:,0],.95)); inner=float(np.clip(measured,-.40,-.24))
    guide['pedestal_fit']={'sample_count':len(sample),'inner_wall_measured_m':measured,'inner_wall_fitted_m':inner}
    width=inner+.77; cx=(inner-.77)/2
    for name,dims,centre in [
        ('Worktop',(1.6,.70,.04),(0,0,.68)),
        ('PedestalSide_L',(.024,.64,.58),(-.788,0,.37)),
        ('PedestalSide_R',(.024,.64,.58),(inner+.012,0,.37)),
        ('PedestalBack',(width,.024,.58),(cx,.308,.37)),
        ('PedestalPlinth',(width-.03,.56,.08),(cx,0,.04)),
        ('PedestalKick',(width-.03,.012,.08),(cx,-.306,.04)),
        ('WorktopFrontReturn',(1.6,.018,.020),(0,-.341,.65)),
        ('WorktopLeftReturn',(.018,.70,.020),(-.791,0,.65)),
        ('WorktopRightReturn',(.018,.70,.020),(.791,0,.65)),
        ('ModestyPanel',(.75-inner,.024,.58),((.75+inner)/2,.26,.37)),
        ('RearUpstand',(1.6,.024,.06),(0,.338,.73)),
        ('LeftUpstand',(.024,.65,.02),(-.788,.0125,.71)),
        ('RightUpstand',(.024,.65,.02),(.788,.0125,.71)),
    ]:panel(name,dims,centre,dark if name in {'PedestalKick','PedestalPlinth'} else paint,.003,parent=body)
    support=empty('EndSupport',parent=body)
    panel('EndPanel',(.035,.64,.66),(.7825,0,.33),paint,.003,parent=support)
    panel('EndShoe',(.035,.60,.016),(.7825,0,.008),dark,.002,parent=support)
    guide['end_support_fit']={'design':'The approved seed 227 and its generated guide have a continuous thin end panel, not an open tube frame. Its closed sheet cage retains the knee well, raised rear lip and below-top rear plate within the layout envelope.'}
    for i,z in enumerate((.17,.36,.55)):
        front=empty(f'Drawer_{i}',(cx,-.325,z),parent=drawers)
        front['slide_axis']='glTF +Z'; front['slide_range_m']=.40
        for name,dims,centre in [
            (f'DrawerFront_{i}',(width-.012,.024,.175),(cx,-.325,z)),
            (f'DrawerSide_L_{i}',(.014,.55,.14),(-.756,-.035,z-.005)),
            (f'DrawerSide_R_{i}',(.014,.55,.14),(inner-.014,-.035,z-.005)),
            (f'DrawerBottom_{i}',(width-.04,.55,.014),(cx,-.035,z-.068)),
            (f'DrawerBack_{i}',(width-.04,.014,.14),(cx,.233,z-.005)),
        ]:
            obj=panel(name,dims,centre,paint,.0015,parent=front)
            if name==f'DrawerFront_{i}':
                recess(obj,(cx,-.333,z+.025),(.12,.016,.040))
        panel(f'DrawerPocket_{i}',(.118,.002,.038),(cx,-.325,z+.025),dark,.0005,parent=front)
        cylinder(f'DrawerPull_{i}',.006,.105,(cx,-.336,z+.025),bare,axis=(1,0,0),sides=16,parent=front)
        rivets(f'DrawerRivets_{i}',[(cx-width/2+.03,-.3375,z),(cx+width/2-.03,-.3375,z)],bare,parent=front)
        SPEC['pivots_gltf'][f'Drawer_{i}']=[cx,z,.325]
    rivets('WorktopRivets',[(x,-.3503,.68) for x in (-.70,.70)],bare,radius=.006,parent=body)
    rivets('PedestalRivets',[(-.788,-.3203,z) for z in (.12,.28,.44,.62)],bare,parent=body)
    data=bpy.data.lights.new('KneeWellStudioFill','AREA')
    light=bpy.data.objects.new('KneeWellStudioFill',data)
    bpy.context.scene.collection.objects.link(light)
    light.location=(0,-2,.25); data.energy=20; data.size=1.5; aim(light,(0,.26,.37))


if __name__=='__main__':
    build_main(__file__,'desk',assemble,SPEC,(1.6,.76,.70))
