import numpy as np
from scipy.fft import fft2,ifft2
from PIL import Image
from pathlib import Path
O=Path(__file__).resolve().parent
im=np.array(Image.open(O.parent/'finish/wear-101.png').convert('RGB'),dtype=float)/255
h,w,c=im.shape;v=np.zeros_like(im);v[0]=im[-1]-im[0];v[-1]=im[0]-im[-1];v[:,0]+=im[:,-1]-im[:,0];v[:,-1]+=im[:,0]-im[:,-1]
den=2*np.cos(2*np.pi*np.arange(h)/h)[:,None]+2*np.cos(2*np.pi*np.arange(w)/w)[None,:]-4;den[0,0]=1
s=fft2(v,axes=(0,1))/den[:,:,None];s[0,0]=0;periodic=np.clip(im-ifft2(s,axes=(0,1)).real,0,1)
Image.fromarray(np.uint8(periodic*255+.5)).save(O/'wear-detail.png')
print('seam edge error before / after',np.abs(im[:,0]-im[:,-1]).mean(),np.abs(periodic[:,0]-periodic[:,-1]).mean())
