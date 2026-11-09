"""Fit the approved generated cabinet bank into separate manufactured parts."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
sys.path.insert(0,str(HERE.parent/'media_cabinet'))
from batch_tools import build_main
from cabinet_fit import assemble_bank

SPEC={'bounds_gltf': [[-1.1, 0, -0.225], [1.1, 0.6, 0.225]], 'required_nodes': ['MediaCabinet', 'Carcass', 'Door_0', 'Door_1', 'Door_2'], 'parents': {'Carcass': 'MediaCabinet', 'Door_0': 'MediaCabinet', 'Door_1': 'MediaCabinet', 'Door_2': 'MediaCabinet'}, 'pivots_gltf': {'MediaCabinet': [0, 0, 0]}, 'materials': ['PaintedSteel', 'BareSteel', 'DarkSteel'], 'visible_details': ['Latch_0', 'Latch_1', 'DoorRivets_0'], 'hero_camera_native': [-2.8, -4.0, 2.1], 'hero_camera_gltf': [-2.8, 2.1, 4], 'hero_target_native': [0, 0, 0.3], 'triangle_limit': 15000, 'room_mount_height_m': 0, 'fit_notes': 'Three faired folded-steel bays retain the generated low cabinet silhouette and layout envelope. Separate closed door leaves have barrel-axis pivots; recessed latches, rivets and kick plates remain independent clean parts.'}


def assemble(guide):
    assemble_bank(guide,SPEC,2.2,0.6,0.45,False)


if __name__=='__main__':
    build_main(__file__,'media_cabinet',assemble,SPEC,(2.2,0.6,0.45))
