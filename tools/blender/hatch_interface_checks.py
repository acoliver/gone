"""Replacement collision/render checks shared by the two construction guards."""
import json
import os
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def check_interfaces(test, build, document, objects, nodes):
    baseline = json.loads((ROOT / "art-source/hatch/hunyuan/baseline-physical.json").read_text())
    by_name = {obj.name: obj for obj in objects}
    for variant, old in zip(document["variants"], baseline["variants"]):
        originals = {row["id"]: row for row in old["frame_solids"]}
        into = variant["hinge_sign"]
        rings = [s for s in variant["frame_solids"] if "/RING/" in s["id"]]
        front = min(s["transform"]["origin"][2] - s["size"][2] / 2 for s in rings) if into > 0 else max(s["transform"]["origin"][2] + s["size"][2] / 2 for s in rings)
        for solid in variant["frame_solids"]:
            if not (solid["id"].startswith("FRAME/") or solid["id"] == "COAMING"):
                continue
            before = originals[solid["id"]]
            np.testing.assert_allclose(solid["size"], before["size"], atol=1e-6, rtol=0)
            np.testing.assert_allclose(solid["transform"]["origin"], before["transform"]["origin"], atol=1e-6, rtol=0)
            np.testing.assert_allclose(solid["transform"]["basis"], before["transform"]["basis"], atol=1e-6, rtol=0)
            np.testing.assert_allclose(solid["vertices"], before["vertices"], atol=1e-6, rtol=0)
            points = np.array([(build.CINV @ v.co.to_4d())[:3]
                               for name, row in nodes.items() if row["kind"] == "frame"
                               and row["variant"] == variant["index"] and row["part"] == solid["index"]
                               for v in by_name[name].data.vertices])
            test.assertGreater(len(points), 24, solid["id"] + " visible edges retain roundovers")
            test.assertLessEqual(float((abs(points) - np.array(solid["size"]) / 2).max()), 1e-6, solid["id"])
            world = points @ np.array(solid["transform"]["basis"]) + solid["transform"]["origin"]
            if solid["id"] != "COAMING":
                test.assertLessEqual(float((into * (front - world[:, 2])).max()), 1e-6, solid["id"] + " ahead of ring")
    # This invokes the unchanged delivered ray grids, culling and both sides,
    # not a permissive box approximation of construction geometry.
    project = Path(os.environ.get("HATCH_TEST_PROJECT", ROOT))
    runner = ROOT / "tests/hatch_interface_guard.gd"
    result = subprocess.run(["godot", "--headless", "--path", str(project), "-s", str(runner)], capture_output=True, text=True)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    test.assertIn("INTERFACE_GUARD PASS", result.stdout.splitlines(), result.stdout + result.stderr)
