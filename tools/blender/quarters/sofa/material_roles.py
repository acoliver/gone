"""Material-slot roles retained by sofa atlas and cloth-only mask baking."""


def role(name):
    if name.startswith('PaintedSteel'): return 'paint'
    if name.startswith('BareSteel'): return 'steel'
    if name.startswith(('Foam', 'FloorDust')): return 'foam'
    if name.startswith(('Oatmeal', 'Wool')): return 'throw'
    if name.startswith(('Charcoal', 'Upholstery')): return 'fabric'
    raise ValueError('Unknown sofa material: ' + name)
