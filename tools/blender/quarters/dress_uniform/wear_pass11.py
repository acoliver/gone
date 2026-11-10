"""Small fold-aligned worn patches and low-amplitude wool drape variation."""
import numpy as np

from wear_pass10 import smoothstep


def body_wear(pattern):
    u, v = np.asarray(pattern).T
    hole = np.zeros(len(u), dtype=bool)
    thinning = np.zeros(len(u))
    for number, (x, height, length, width) in enumerate([
            (.12, .38, .0045, .0032), (.37, .62, .0041, .0026),
            (.325, .24, .0034, .0024), (.075, .58, .0028, .0021),
            (.425, .46, .0032, .0023), (.77, .43, .0044, .0027),
            (.92, .64, .0034, .0022)]):
        along = (v-height)/(length*1.5)
        center = x+.0009*np.sin(along*2.1+number)
        across = (u-center)/(width*1.5)
        angle = np.arctan2(along, across)
        radius = np.sqrt(across**2+along**2)
        edge = 1+.17*np.sin(angle*5+number)+.10*np.sin(angle*9+number*.7)
        hole |= radius < edge*.72
        thinning = np.maximum(thinning, np.exp(-((radius/(edge*1.65))**2)))
    seam = np.exp(-((u-.442)/.008)**2)*np.exp(-((v-.40)/.25)**4)
    fold = np.exp(-((u-(.23+.008*np.sin(v*18)))/.012)**2)*np.exp(-((v-.52)/.25)**4)
    thinning = np.maximum(thinning, .65*np.maximum(seam, fold))
    allowed = (u < 1.) & (v > .12) & (v < .78)
    fade = .16+.10*np.sin(u*53+v*5)*(.4+.6*np.sin(v*8)**2)+.035*np.sin(u*91-v*17)
    return dict(hole=hole & allowed, thinning=thinning*allowed, fade=np.clip(fade, .03, .35))


def wool_displacement(points, pattern):
    points, pattern = np.asarray(points), np.asarray(pattern)
    x, y, z = points.T
    mask = smoothstep((-z-.36)/.10)*smoothstep((z+.83)/.09)
    mask *= smoothstep((abs(x)-.03)/.035)*(pattern[:, 0] < 1.)
    phase = x*47+z*16+.42*np.sin(z*24)
    delta = np.zeros_like(points)
    delta[:, 1] = mask*(.0017*np.sin(phase)+.00065*np.sin(x*81-z*33))
    delta[:, 2] = -mask*.00085*(.5+.5*np.sin(x*31+z*18))
    return delta


def lip_loss(stations, supporting_depth):
    stations = np.asarray(stations)
    loss = np.full(stations.shape, .0016)
    for wavelength, amplitude in [(.0081, .0013), (.0033, .0009), (.0015, .0006)]:
        t = stations/wavelength
        cell = np.floor(t)
        a = (np.sin(cell*12.9898+96.11)*43758.5453) % 1
        b = (np.sin((cell+1)*12.9898+96.11)*43758.5453) % 1
        loss += amplitude*(2*(a+(b-a)*smoothstep(t-cell))-1)
    return np.maximum(0., np.minimum(loss, .35*np.asarray(supporting_depth)))
