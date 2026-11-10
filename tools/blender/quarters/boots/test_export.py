"""The inner shaft must stay inside the boot exterior at every sampled level."""
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
from verify import ROOT, load


def cavity_failures(mesh):
    low,high=mesh.bounds[:,1]
    failures=[]
    # A curled open lip can legitimately split horizontal sections into islands.
    for height in np.linspace(low+.001,low+(high-low)*.85,160):
        section=mesh.section([0,1,0],[0,height,0])
        if section is None:
            continue
        polygons=sorted((Polygon(path[:,[0,2]]) for path in section.discrete),
                        key=lambda polygon:polygon.area,reverse=True)
        if any(not polygon.is_valid for polygon in polygons):
            failures.append(float(height))
        elif len(polygons)>1 and any(not polygons[0].covers(polygon) for polygon in polygons[1:]):
            failures.append(float(height))
    return failures


class ShaftContainmentTests(unittest.TestCase):
    def test_clean_and_aged_cavities_stay_inside_outer_shell(self):
        for suffix in ['', '_aged']:
            _,meshes=load(ROOT/f'assets/props/quarters/boots{suffix}.glb')
            for name,mesh in meshes.items():
                if name.startswith('LeatherUpper'):
                    with self.subTest(state=suffix or 'remembered',part=name):
                        self.assertEqual(cavity_failures(mesh),[])


if __name__=='__main__':
    unittest.main()
