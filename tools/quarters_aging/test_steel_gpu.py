"""GPU ownership follows generator processes, not shell commands waiting for them."""
import unittest

from steel_library import gpu_jobs


class GPUJobTests(unittest.TestCase):
    def test_waiting_shells_and_supervisors_are_not_generators(self):
        snapshot = ('12 bash -c while ps | grep -E "mflux|generate.py" | grep -v grep; do sleep 3; done\n'
                    '13 bun --eval spawn bash grep mflux-generate\n'
                    '14 python tools/quarters_aging/refine_library.py\n')
        self.assertEqual(gpu_jobs(snapshot), [])

    def test_actual_generators_are_detected(self):
        jobs = ['21 python /tools/mflux-generate-flux2-edit --steps 4',
                '22 python /other/generate.py --seed 10']
        self.assertEqual(gpu_jobs('\n'.join(jobs)+'\n23 godot --headless'), jobs)


if __name__ == '__main__':
    unittest.main()
