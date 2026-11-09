"""Fair the approved desk chair guide into separate steel and pad parts."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
sys.path.insert(0,str(HERE.parent/'desk_chair'))
from batch_tools import build_main
from chair_fit import assemble_chair

SPEC={
    'bounds_gltf':[[-.25,0,-0.25],[.25,0.95,0.25]],
    'required_nodes':['Chair','Frame','SeatPan','SeatPad','BackPlate'],
    'parents':{'Frame':'Chair','SeatPan':'Frame','SeatPad':'Chair','BackPlate':'Frame'},
    'pivots_gltf':{'Chair':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel','Fabric'],
    'paint_color':[.080,.095,.070,1],
    'visible_details':['SeatPad','BackPlate'],
    'hero_camera_native':[-1.5,-2.5,1.6],'hero_camera_gltf':[-1.5,1.6,2.5],
    'hero_target_native':[0,0,0.475],'triangle_limit':6000,
    'fit_notes':'The generated seat patch determines sitting height within an ergonomic .42-.46 m range. Its frame and back surfaces are faired to sparse manufactured panels and beams, preserving the four-legged silhouette and the separate thin seat pad. No textures or aging.',
}


def assemble(guide):
    assemble_chair(guide,SPEC,0.95,0.5)


if __name__=='__main__':
    build_main(__file__,'desk_chair',assemble,SPEC,(.5,0.95,0.5))
