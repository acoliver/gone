"""Round 3 hatch construction probes, run with Blender --background --python-exit-code 1.

Each corrected source defect has one probe that reads the built mesh or the exported
source, not new attributes. Guards pin the geometry that must not change.
HATCH_SOURCE_JSON selects the exported source (default: tmp/hatch-model/parts-source.json).
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("HATCH_SOURCE_JSON", ROOT / "tmp/hatch-model/parts-source.json"))
spec = importlib.util.spec_from_file_location("build_hatch", Path(__file__).with_name("build_hatch.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def source_matrix(pose):
    basis, origin = pose["basis"], pose["origin"]
    matrix = Matrix.Identity(4)
    for column in range(3):
        for row in range(3):
            matrix[row][column] = basis[column][row]
        matrix[column][3] = origin[column]
    return matrix


def source_points(obj, solid_transform=None):
    # Mesh vertices are stored in Blender space; CINV recovers part-local source space.
    points = [(build.CINV @ vertex.co.to_4d()).to_3d() for vertex in obj.data.vertices]
    if solid_transform is None:
        return points
    matrix = source_matrix(solid_transform)
    return [(matrix @ point.to_4d()).to_3d() for point in points]


def hull(points):
    unique = sorted({(round(p.x, 9), round(p.y, 9)) for p in points})

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def inside_convex(polygon, x, y, tolerance=1e-6):
    for index in range(len(polygon)):
        ax, ay = polygon[index]
        bx, by = polygon[(index + 1) % len(polygon)]
        length = ((bx - ax) ** 2 + (by - ay) ** 2) ** .5
        signed = ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / length
        if signed < -tolerance:
            return False
    return True


def forged_section_ratio(section):
    # Driver 2026-11-06: the raw ratio penalised flat bars for their aspect
    # ratio. Normalise by each half-extent so rectangles score sqrt(2) and
    # ellipses score 1, preserving the 1.15 non-roundness threshold.
    lo = Vector((min(p.x for p in section), min(p.y for p in section)))
    hi = Vector((max(p.x for p in section), max(p.y for p in section)))
    center = (lo + hi) / 2
    half = (hi - lo) / 2
    points = [Vector(((p.x - center.x) / half.x,
                      (p.y - center.y) / half.y)) for p in section]
    axis = max(abs(p.x) for p in points)
    diagonal = max((abs(p.x) + abs(p.y)) / 2 ** .5 for p in points)
    return diagonal / axis


class HatchRound3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        cls.document = __import__("json").loads(SOURCE.read_text())
        from hatch_generated_frame import load_frames
        cls.objects, cls.nodes, cls.error = build.construct(cls.document, build.material(), load_frames(cls.document))
        cls.by_name = {obj.name: obj for obj in cls.objects}

    def test_leaf_rivets_follow_one_pitch_around_each_run(self):
        # Each run is one closed loop; consecutive centres around it must share one pitch.
        for variant in self.document["variants"]:
            for group in variant["groups"]:
                if not group["path"].endswith("Rivets"):
                    continue
                centres = [Vector(part["transform"]["origin"][:2]) for part in group["parts"]]
                gaps = [(centres[(index + 1) % len(centres)] - centres[index]).length
                        for index in range(len(centres))]
                self.assertGreaterEqual(min(gaps), .12, group["path"] + " crowded rivet pair")
                self.assertLessEqual(max(gaps) / min(gaps), 1.05, group["path"] + " uneven pitch")
                self.assertLessEqual(max(gaps), .17, group["path"] + " sparse rivet pair")

    def test_leaf_rivets_keep_inset_from_plate_edge(self):
        for variant in self.document["variants"]:
            plate = next(part for group in variant["groups"] for part in group["parts"]
                         if group["steel"] and part["id"].endswith("Steel/plate") and group["side"] == 0)
            half = [value / 2 for value in plate["size"][:2]]
            centre_x, centre_y = plate["transform"]["origin"][:2]
            for group in variant["groups"]:
                if not group["path"].endswith("Rivets"):
                    continue
                for part in group["parts"]:
                    x, y = part["transform"]["origin"][:2]
                    self.assertGreaterEqual(min(half[0] - abs(x - centre_x), half[1] - abs(y - centre_y)), .04, part["id"])

    def test_throat_has_one_rear_depth_around_the_opening(self):
        for variant in self.document["variants"]:
            rears = {round(solid["transform"]["origin"][2] + solid["size"][2] / 2, 6)
                     for solid in variant["frame_solids"] if "/THROAT/" in solid["id"]}
            self.assertEqual(len(rears), 1, "throat rear depths " + str(sorted(rears)))

    def test_guard_collision_reservations_trimmed_rendering_and_both_sided_seals(self):
        # Driver decision: drawn boxes no longer equal collision boxes. Preserve
        # collision to 1 um, contained/behind-ring rounded interfaces, and the
        # unchanged zero-miss seal/pocket grids on both sides. Threshold exempt.
        from hatch_interface_checks import check_interfaces
        check_interfaces(self, build, self.document, self.objects, self.nodes)

    def test_hinge_caps_are_seated_with_a_neck(self):
        checked = 0
        for name, row in self.nodes.items():
            if row["kind"] != "leaf" or "StrapHinges" not in row["id"] or "/cap-" not in row["id"]:
                continue
            checked += 1
            points = source_points(self.by_name[name])
            radii = [(point.x ** 2 + point.z ** 2) ** .5 for point in points]
            low = min(points, key=lambda p: p.y).y
            high = max(points, key=lambda p: p.y).y
            end_radii = [max(r for p, r in zip(points, radii) if abs(p.y - end) < 1e-6) for end in (low, high)]
            self.assertLessEqual(min(end_radii) / max(radii), .6, row["id"] + " flat disc without neck")
        self.assertGreater(checked, 0)

    def test_whole_latch_mid_arm_retains_a_flat_sided_section(self):
        checked = 0
        for name, row in self.nodes.items():
            if row["kind"] != "leaf" or "Lugs" not in row["id"] or "/whole-" not in row["id"]:
                continue
            checked += 1
            variant = self.document['variants'][row['variant']]
            part = variant['groups'][row['group']]['parts'][row['part']]
            points = source_points(self.by_name[name], part['transform'])
            direction = Vector((.14, .035, 0)).normalized()
            across = Vector((direction.y, -direction.x, 0))
            pivot = Vector(part['transform']['origin']) - Vector((.069857674387797, .034979292176354, -.031947860536794))
            middle = pivot + Vector((.07, .0175, 0))
            section = []
            for face in self.by_name[name].data.polygons:
                corners = [points[index] for index in face.vertices]
                distances = [(point - middle).dot(direction) for point in corners]
                for i, j in [(0, 1), (1, 2), (2, 0)]:
                    if (distances[i] < 0) == (distances[j] < 0): continue
                    point = corners[i].lerp(corners[j], -distances[i] / (distances[j] - distances[i]))
                    section.append(Vector((point.dot(across), point.z)))
            self.assertGreater(len(section), 3, 'actual whole-latch mid-arm section')
            lo = Vector((min(p.x for p in section), min(p.y for p in section)))
            hi = Vector((max(p.x for p in section), max(p.y for p in section)))
            ratio = forged_section_ratio(section)
            print('WHOLE_LATCH_SECTION', row['id'], 'width_m', hi.x-lo.x,
                  'depth_m', hi.y-lo.y, 'diagonal_over_axis', ratio,
                  'required', 1.15, flush=True)
            self.assertGreater(ratio, 1.15, row["id"] + " round cross-section")
        self.assertGreater(checked, 0)

    def test_guard_fixed_ring_is_constant_width_with_fifty_four_rivets_per_face(self):
        for variant in self.document["variants"]:
            widths = []
            for solid in variant["frame_solids"]:
                if "/RING/" not in solid["id"]:
                    continue
                a, b, _, d = (Vector(p) for p in solid["section"])
                edge = (b - a).normalized()
                widths.append(abs(edge.x * (d - a).y - edge.y * (d - a).x))
            # Section vertices are exported as float32, so compare at micrometre scale.
            # Andrew's 2026-11-05 raised bead replaces the 160 mm band.
            # Equal arc pitch remains unchanged as its shorter centreline loses stations.
            self.assertAlmostEqual(min(widths), .09, delta=1e-6)
            self.assertAlmostEqual(max(widths), .09, delta=1e-6)
            for side in (0, 1):
                self.assertEqual(sum(1 for rivet in variant["frame_rivets"] if rivet["side"] == side), 54)

    def test_guard_original_reservations_stay_exact(self):
        self.assertLess(self.error, 1e-6)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(HatchRound3Test)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise RuntimeError("hatch round 3 probes failed")
