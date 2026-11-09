"""Deterministic finishing fields in physical and original pattern coordinates."""
import numpy as np


def smoothstep(value):
    value = np.clip(value, 0., 1.)
    return value*value*(3-2*value)


def finishing_displacement(points, pattern):
    points, pattern = np.asarray(points), np.asarray(pattern)
    x, y, z = points.T
    u, v = pattern.T
    delta = np.zeros_like(points)
    body = u < 1.
    rear = body & (u > .48)
    shoulder = smoothstep((x-.16)/.025)*smoothstep((.256-x)/.035)
    shoulder *= smoothstep((v-.85)/.09)*rear
    delta[:, 1] += .017*shoulder
    hem = body*smoothstep((-z-.75)/.075)*smoothstep((np.abs(x)-.03)/.025)
    losses = smoothstep((z+.875)/.05)
    delta[:, 2] += hem*losses*(.014+.012*np.exp(-((x-.08)/.035)**2)+
                               .009*np.exp(-((x+.09)/.023)**2))
    bag = smoothstep((-z-.36)/.12)*smoothstep((z+.80)/.12)*body
    bag *= smoothstep((np.abs(x)-.03)/.025)
    delta[:, 1] += bag*.0035*np.sin(x*26+z*14)*np.sin(z*19+.7)
    return delta


def ragged_erosion(points, seed):
    p = np.asarray(points)
    station = p[:, 0]*.79+p[:, 1]*.47+p[:, 2]*.63
    erosion = np.full(len(p), .0032)
    for octave, (length, amplitude) in enumerate(zip([.0091, .0043, .0019, .00083],
                                                    [.0027, .0015, .00075, .00035])):
        t = station/length
        cell = np.floor(t)
        phase = cell*12.9898+(seed+octave)*.123
        a = np.mod(np.sin(phase)*43758.5453, 1)*2-1
        b = np.mod(np.sin(phase+12.9898)*43758.5453, 1)*2-1
        erosion += amplitude*(a+(b-a)*smoothstep(t-cell))
    return np.clip(erosion, .0002, .0065)


def body_wear(pattern):
    pattern = np.asarray(pattern)
    u, v = pattern.T
    hole = np.zeros(len(pattern), dtype=bool)
    thinning = np.zeros(len(pattern))
    for x, height, length, width in [(.12, .38, .010, .0009), (.37, .62, .008, .0012),
                                     (.325, .24, .007, .0008), (.075, .58, .003, .0016),
                                     (.425, .46, .004, .0010), (.77, .43, .010, .0009),
                                     (.92, .64, .006, .0010)]:
        along = (v-height)/length
        center = x+.00025*np.sin((v-height)*950+x*17)
        across = (u-center)/width
        ragged = 1+.20*np.sin(v*2300+x*29)+.12*np.sin(v*4700)
        hole |= (across**2+(along*1.0)**4 < ragged) & (np.abs(along) < 1)
        thinning = np.maximum(thinning, np.exp(-((u-center)/(.009+width))**2-along**2*.12))
    seam = np.exp(-((u-.442)/.008)**2)*np.exp(-((v-.40)/.25)**4)
    fold = np.exp(-((u-(.23+.008*np.sin(v*18)))/.012)**2)*np.exp(-((v-.52)/.25)**4)
    thinning = np.maximum(thinning, .65*np.maximum(seam, fold))
    allowed = (u < 1.) & (v > .12) & (v < .78)
    return dict(hole=hole & allowed, thinning=thinning*allowed)
