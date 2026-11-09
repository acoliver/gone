"""Deterministic rectangular packing for sofa material islands."""


def rectangles(items, size):
    free = [(0, 0, size, size)]
    result = {}
    for name, width, height in sorted(items, key=lambda i: (-i[2], -i[1], i[0])):
        free.sort(key=lambda r: (r[1], r[0]))
        index = next((i for i, (_, _, w, h) in enumerate(free) if w >= width and h >= height), None)
        if index is None:
            raise ValueError('Sofa material atlas is full: ' + name)
        x, y, w, h = free.pop(index)
        result[name] = [x, y, width, height]
        if w > width:
            free.append((x + width, y, w - width, height))
        if h > height:
            free.append((x, y + height, w, h - height))
    return result
