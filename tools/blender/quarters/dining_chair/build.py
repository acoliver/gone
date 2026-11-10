"""Fair the approved dining chair guide into separate steel and pad parts."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
sys.path.insert(0,str(HERE.parent/'desk_chair'))
from batch_tools import build_main
from chair_fit import assemble_chair

SPEC={
    'bounds_gltf':[[-.25,0,-0.225],[.25,0.9,0.225]],
    'required_nodes':['Chair','Frame','SeatPan','SeatPad','BackPlate'],
    'parents':{'Frame':'Chair','SeatPan':'Frame','SeatPad':'Chair','BackPlate':'Frame'},
    'pivots_gltf':{'Chair':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel','Fabric'],
    'paint_color':[.080,.095,.070,1],
    'round_frame':True,
    'back_gap_m':.08,
    'pad_height_m':.04,
    'visible_details':['SeatPad','BackPlate'],
    'hero_camera_native':[-1.5,-2.5,1.6],'hero_camera_gltf':[-1.5,1.6,2.5],
    'hero_target_native':[0,0,0.45],'triangle_limit':6000,
    'fit_notes':'The generated seat patch determines sitting height within an ergonomic .42-.46 m range. Round steel tubes, cylindrical dark shoes, a rounded back plate with visible corner rivets and an 80 mm back gap follow seed 263. The separate 40 mm pad rests inside a folded steel pan lip. No textures or aging.',
}


def assemble(guide):
    assemble_chair(guide,SPEC,0.9,0.45)


if __name__=='__main__':
    build_main(__file__,'dining_chair',assemble,SPEC,(.5,0.9,0.45))
