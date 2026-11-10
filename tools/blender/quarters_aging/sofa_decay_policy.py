"""Fixed fitted-to-settled order and per-cover variation for the dense sofa."""
ORDER = ('SeatCushion_C', 'SeatCushion_L', 'SeatCushion_R',
         'BackCushion_C', 'BackCushion_L', 'BackCushion_R')
UPHOLSTERY = (.055, .060, .066)
FOAM = (.16, .065, .022)
DECK = .3898


def cushion_plan(name):
    index = ORDER.index(name)
    back = name.startswith('Back')
    return {'seed': 9601+index*37, 'back': back, 'pins': 0,
            'settled_contacts': list(ORDER[:index]),
            'residue_height_scale': (1., .85, 1.15)[index % 3] if back else (.68, .56, .82)[index],
            'rest_depth_scale': (.58, .65, .51)[index % 3] if back else 1.,
            'rest_height_scale': 1. if back else (.28, .23, .34)[index],
            'collapse_frames': 180, 'frames': 300 if back else 320}
