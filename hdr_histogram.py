"""RGB histogram of the linear HDR master, independent of SDR tone mapping.

SDR occupies the left half in sRGB encoding. The right half spans +0..+6 EV
above linear reference white (1.0). Values above +6 EV remain in the last bin.
Computed by the existing preview worker, never by the UI paint callback.
"""
import numpy as np

SDR_BINS=256
HDR_STOPS=6
HDR_BINS=192
SDR_SHARE=.55

def build(linear):
    a=np.asarray(linear)
    if a.ndim!=3 or a.shape[2]!=3:raise ValueError('Expected an RGB histogram source')
    pixels=a.reshape(-1,3)
    pixels=pixels[np.isfinite(pixels).all(axis=1)]
    channels=[]
    for values in pixels.T:
        low=np.clip(values[values<=1],0,1)
        encoded=np.where(low<=.0031308,low*12.92,1.055*low**np.float32(1/2.4)-.055)
        sdr=np.histogram(np.clip(encoded,0,1),bins=SDR_BINS,range=(0,1))[0]
        high=values[values>1]
        hdr=np.histogram(np.minimum(np.log2(high),HDR_STOPS),bins=HDR_BINS,range=(0,HDR_STOPS))[0]
        channels.append(np.concatenate((sdr,hdr)))
    maximum=np.maximum(pixels.max(axis=1),0) if len(pixels) else np.empty(0,np.float32)
    return {'bins':channels,'samples':len(pixels),'invalid':a.shape[0]*a.shape[1]-len(pixels),
            'peak_ev':float(np.log2(max(float(maximum.max()),1e-8))) if len(maximum) else None,
            'hdr_fraction':float(np.mean(maximum>1)) if len(maximum) else 0.,
            'black_fraction':float(np.mean(np.any(pixels<=0,axis=1))) if len(maximum) else 0.,
            'overflow_fraction':float(np.mean(maximum>2.**HDR_STOPS)) if len(maximum) else 0.}

def positions():
    # Counts are per interval. Place each interval at its horizontal center.
    return np.concatenate(((np.arange(SDR_BINS)+.5)/SDR_BINS*SDR_SHARE,
                           SDR_SHARE+(np.arange(HDR_BINS)+.5)/HDR_BINS*(1-SDR_SHARE)))
