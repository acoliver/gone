"""Physical-radius normal rounding and material-isolated photographic maps."""
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.special import ndtr


def rounded_facet_normals(points, planes, radius):
    """Blend adjacent struck facets within a measured physical ridge footprint."""
    angle=np.mod(np.arctan2(points[...,0],points[...,2]),2*np.pi)
    sector=np.floor(angle/(np.pi/5)).astype(int)
    radial=np.hypot(points[...,0],points[...,2])
    lower=radial*np.sin(angle-sector*np.pi/5)
    upper=radial*np.sin((sector+1)*np.pi/5-angle)
    a=ndtr(-lower/(radius*.5));b=ndtr(-upper/(radius*.5))
    result=(1-a-b)[...,None]*planes[sector]+a[...,None]*planes[(sector-1)%10]+b[...,None]*planes[(sector+1)%10]
    return result/np.linalg.norm(result,axis=-1)[...,None]


def remove_row_bands(detail, rib_cycles):
    """Remove photographed horizontal marks outside the resolved grosgrain band."""
    spectrum=np.fft.rfft(detail,axis=0);frequency=np.arange(len(spectrum))
    reject=(frequency<rib_cycles*.7)|(frequency>rib_cycles*1.4)
    spectrum[reject]=0
    result=np.fft.irfft(spectrum,n=len(detail),axis=0)
    return result-result.mean()


def material_padding(values,mask):
    """Every out-of-island texel inherits only this material's nearest sample."""
    assert mask.any(),'Cannot pad an empty material'
    nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True)
    return values[tuple(nearest)]
