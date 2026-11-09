"""Fit the approved generated cabinet bank into separate manufactured parts."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
sys.path.insert(0,str(HERE.parent/'media_cabinet'))
from batch_tools import build_main
from cabinet_fit import assemble_bank

SPEC={'bounds_gltf': [[-1.35, 0, -0.2], [1.35, 0.6, 0.2]], 'required_nodes': ['OverBedLockers', 'Carcass', 'Door_0', 'Door_1', 'Door_2', 'Module_0', 'Module_1', 'Module_2'], 'parents': {'Carcass': 'OverBedLockers', 'Door_0': 'Module_0', 'Door_1': 'Module_1', 'Door_2': 'Module_2'}, 'pivots_gltf': {'OverBedLockers': [0, 0, 0]}, 'materials': ['PaintedSteel', 'BareSteel', 'DarkSteel'], 'visible_details': ['Latch_0', 'Latch_1', 'DoorRivets_0'], 'hero_camera_native': [-2.8, -4.0, 2.1], 'hero_camera_gltf': [-2.8, 2.1, 4], 'hero_target_native': [0, 0, 0.3], 'triangle_limit': 15000, 'room_mount_height_m': 1.9, 'fit_notes': 'Three equal bays fair the approved generated cabinet silhouette. Manufactured closed sheet cages replace scan noise. Door leaves have their own barrel-axis origins; latches and rivet heads are separate geometry. Wall units retain a local floor-centred origin and are mounted at room y=1.9.'}


def assemble(guide):
    assemble_bank(guide,SPEC,2.7,0.6,0.4,True)


if __name__=='__main__':
    build_main(__file__,'lockers_over_bed',assemble,SPEC,(2.7,0.6,0.4))
