"""Present bezel photo synthesis and masked spatial-periodicity measurements."""
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from scipy.signal import fftconvolve


def synthesize(crops, size, seed=13010):
    """Overlap rotated photo patches at jittered positions, with no wrapped tile."""
    rng=np.random.default_rng(seed)
    total=np.zeros((size,size),np.float64);weight=np.zeros_like(total)
    patch_size=min(min(c.shape) for c in crops)
    step=max(2,patch_size//3)
    for row in range(-patch_size,size+patch_size,step):
        for col in range(-patch_size,size+patch_size,step):
            crop=crops[int(rng.integers(len(crops)))];crop=np.rot90(crop,int(rng.integers(4)))
            if rng.integers(2):crop=crop[:,::-1]
            sy=int(rng.integers(crop.shape[0]-patch_size+1));sx=int(rng.integers(crop.shape[1]-patch_size+1))
            patch=crop[sy:sy+patch_size,sx:sx+patch_size]
            y=row+int(rng.integers(-step//2,step//2+1));x=col+int(rng.integers(-step//2,step//2+1))
            y0,y1=max(y,0),min(y+patch_size,size);x0,x1=max(x,0),min(x+patch_size,size)
            if y1<=y0 or x1<=x0:continue
            axis=np.hanning(patch_size+2)[1:-1];window=axis[:,None]*axis[None,:]
            section=np.s_[y0-y:y1-y,x0-x:x1-x];w=window[section]
            total[y0:y1,x0:x1]+=patch[section]*w;weight[y0:y1,x0:x1]+=w
    assert np.all(weight>0),'Photo synthesis left holes'
    result=total/weight
    result-=result.mean()
    return result.astype(np.float32)


def periodicity(image, mask, pixels_per_mm, old_period_mm=1.134940552372772):
    """Pairwise Pearson autocorrelation after removing broad illumination.

    Each lag uses its own overlapping-mask means and variances. The search is
    0.65..3.5 mm; it excludes the central autocorrelation lobe and distant aliases.
    """
    image=np.asarray(image,float);mask=np.asarray(mask,bool)
    support=gaussian_filter(mask.astype(float),max(.2*pixels_per_mm,1))
    smooth=gaussian_filter(np.where(mask,image,0),max(.2*pixels_per_mm,1))/np.maximum(support,1e-12)
    residual=np.where(mask,image-smooth,0)
    m=mask.astype(float)
    corr=lambda a,b:fftconvolve(a,b[::-1,::-1],mode='full')
    count=corr(m,m);sum_a=corr(residual,m);sum_b=corr(m,residual)
    var_a=np.maximum(corr(residual**2,m)-sum_a**2/np.maximum(count,1),0)
    var_b=np.maximum(corr(m,residual**2)-sum_b**2/np.maximum(count,1),0)
    rho=(corr(residual,residual)-sum_a*sum_b/np.maximum(count,1))/np.maximum(np.sqrt(var_a*var_b),1e-15)
    yy,xx=np.indices(rho.shape);dy=yy-image.shape[0]+1;dx=xx-image.shape[1]+1
    distance=np.hypot(dx,dy)/pixels_per_mm
    valid=(count>max(200,mask.sum()*.08))&(distance>=.65)&(distance<=3.5)
    peaks=valid&(rho==maximum_filter(rho,size=5))
    assert peaks.any(),'Insufficient spatial samples for periodicity'
    strongest=float(rho[peaks].max())
    tied=peaks&(rho>=strongest-1e-6)
    index=np.unravel_index(np.argmin(np.where(tied,distance,np.inf)),rho.shape)
    # The old crop repeats on both physical axes, not around polar UV seams.
    near=valid&((abs(abs(dx)/pixels_per_mm-old_period_mm)<.12)&(abs(dy)/pixels_per_mm<.12)|(abs(abs(dy)/pixels_per_mm-old_period_mm)<.12)&(abs(dx)/pixels_per_mm<.12))
    old_index=np.unravel_index(np.argmax(np.where(near,rho,-np.inf)),rho.shape)
    return dict(dominant_period_mm=float(distance[index]),dominant_lag_mm=[float(dx[index]/pixels_per_mm),float(dy[index]/pixels_per_mm)],dominant_peak_correlation=float(rho[index]),old_period_peak_correlation=float(rho[old_index]),old_period_lag_mm=[float(dx[old_index]/pixels_per_mm),float(dy[old_index]/pixels_per_mm)],mask_pixels=int(mask.sum()),pixels_per_mm=float(pixels_per_mm),search_mm=[.65,3.5],broad_illumination_gaussian_sigma_mm=.2)
