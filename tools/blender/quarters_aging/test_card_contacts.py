"""Fringe placement uses the same SAT narrow phase as the exported gate."""
from types import SimpleNamespace
import unittest

import numpy as np

from card_contacts import CardContacts


class CardPlacement(unittest.TestCase):
    def setUp(self):
        points = [(-1, -1, 0), (1, -1, 0), (0, 1, 0)]
        data = SimpleNamespace(vertices=[SimpleNamespace(co=np.array(p)) for p in points],
                               loop_triangles=[SimpleNamespace(vertices=(0, 1, 2))],
                               calc_loop_triangles=lambda: None)
        self.contacts = CardContacts([SimpleNamespace(data=data, matrix_world=np.eye(3))])

    def test_lifted_card_is_clear_but_crossing_card_is_rejected(self):
        clear = np.array([(-.1, -.1, .002), (.1, -.1, .002), (.1, .1, .002), (-.1, .1, .002)])
        self.assertTrue(self.contacts.clear(clear))
        crossing = clear.copy()
        crossing[:2, 2] *= -1
        self.assertFalse(self.contacts.clear(crossing))

    def test_accepted_cards_block_later_card_overlap(self):
        card = np.array([(-.1, -.1, .002), (.1, -.1, .002), (.1, .1, .002), (-.1, .1, .002)])
        self.contacts.add(card)
        self.assertFalse(self.contacts.clear(card))


if __name__ == '__main__':
    unittest.main()
