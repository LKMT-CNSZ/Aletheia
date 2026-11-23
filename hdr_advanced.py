"""Opt-in HDR shaping; neutral defaults preserve all existing recipes exactly."""
import numpy as np

FIELDS=('hdr_chroma','hdr_sky_protect','hdr_target','hdr_curve','sdr_hdr_contrast','sdr_hdr_highlights','sdr_hdr_saturation','hdr_punch','hdr_brilliance','sdr_hdr_color_safe')

def color_safe_active(p):return p.sdr_hdr_color_safe

def impact_active(p):
    return bool(p.hdr_punch or p.hdr_brilliance)

def active(p):
    return bool(color_safe_active(p) or impact_active(p) or p.hdr_chroma or p.hdr_sky_protect or p.hdr_target!='all' or p.hdr_curve!=[[0.,0.],[1.,1.]] or p.sdr_hdr_contrast or p.sdr_hdr_highlights or p.sdr_hdr_saturation)

def color_safe_sdr(rgb):
    """Common RGB gain with a smooth shoulder; no added white/channel clipping."""
    maximum=np.maximum(rgb.max(axis=-1,keepdims=True),0)
    delta=np.maximum(maximum-.85,0);mapped=.85+delta/(1+delta/.15)
    return (rgb*np.where(maximum>.85,mapped/np.maximum(maximum,1e-8),1)).astype(np.float32)

def brilliance(linear,weight,amount):
    """Move very bright colored light toward white, retaining RGB hue direction.

    Saturated red/blue highlights alone can have low perceived luminance even
    when a component is above white. This opt-in blend adds radiance to the
    other components instead of just driving one channel beyond the display.
    """
    if not amount:return linear
    maximum=linear.max(axis=-1)
    t=np.clip((maximum-1)/2,0,1);t=t*t*(3-2*t)
    mix=np.float32(amount)*weight*t
    return (linear+(maximum[...,None]-linear)*mix[...,None]).astype(np.float32)

def weights(linear,p,luma_weight):
    """Color signal uses strongest channel; dark chroma cannot acquire a glow."""
    x=np.maximum(linear,0);maximum=x.max(axis=-1);minimum=x.min(axis=-1)
    saturation=(maximum-minimum)/np.maximum(maximum,1e-8)
    t=np.clip((maximum-p.hdr_start)/p.hdr_softness,0,1);t=t*t*(3-2*t)
    weight=np.maximum(luma_weight,t*saturation*p.hdr_chroma)
    r,g,b=np.moveaxis(x,-1,0)
    blue=np.clip((b-np.maximum(r,g))/np.maximum(maximum,1e-8),0,1)
    # Smooth color mask, not semantic sky detection; also affects blue objects.
    weight*=(1-p.hdr_sky_protect*np.clip(blue*4,0,1))**3
    if p.hdr_target!='all':
        signal={'red':r,'green':g,'blue':b,'magenta':np.minimum(r,b)}[p.hdr_target]
        other={'red':np.maximum(g,b),'green':np.maximum(r,b),'blue':np.maximum(r,g),'magenta':g}[p.hdr_target]
        weight*=np.clip((signal-other)/np.maximum(maximum,1e-8)*3,0,1)
    return np.clip(weight,0,1)

def curve(linear,points):
    if points==[[0.,0.],[1.,1.]]:return linear
    import core
    maximum=np.maximum(linear.max(axis=-1),0)
    u=np.log2(1+maximum)/np.log2(65.)
    lut=core.curve_lut(points)
    mapped=np.interp(np.clip(u,0,1),np.linspace(0,1,len(lut)),lut)
    target=np.exp2(mapped*np.log2(65.))-1
    # Continue the last segment beyond +6 EV instead of flattening brighter data.
    slope=(points[-1][1]-points[-2][1])/max(points[-1][0]-points[-2][0],1e-8)
    beyond=np.maximum(u-1,0)*slope
    target=np.where(u>1,np.exp2((points[-1][1]+beyond)*np.log2(65.))-1,target)
    mapped=linear*(target/np.maximum(maximum,1e-8))[...,None]
    return np.where((maximum<=1e-8)[...,None],target[...,None],mapped).astype(np.float32)

def sdr_controls(out,p):
    import core
    if not (impact_active(p) or p.sdr_hdr_contrast or p.sdr_hdr_highlights or p.sdr_hdr_saturation):return out
    y=np.maximum(core.luma(out,p.working_space),0)
    target=.18*(np.maximum(y,1e-8)/.18)**np.float32(2.**(p.sdr_hdr_contrast*.5))
    weight=np.clip(y,0,1)**2
    target*=np.exp2(weight*p.sdr_hdr_highlights)
    rgb=out*(target/np.maximum(y,1e-8))[...,None]
    saturation=np.exp2(p.sdr_hdr_saturation*weight)[...,None]
    rgb=target[...,None]+(rgb-target[...,None])*saturation
    rgb=np.maximum(rgb,0)
    # Fit colored highlights to SDR without independently clipping channels.
    maximum=rgb.max(axis=-1,keepdims=True)
    if impact_active(p):
        delta=np.maximum(maximum-.8,0);mapped=.8+delta/(1+delta/.2)
        return (rgb*np.where(maximum>.8,mapped/np.maximum(maximum,1e-8),1)).astype(np.float32)
    return (rgb/np.maximum(maximum,1)).astype(np.float32)

def report(linear):
    if linear is None:return None
    x=np.asarray(linear);sample=x[::max(1,x.shape[0]//400),::max(1,x.shape[1]//400)]
    maximum=np.maximum(sample.max(axis=-1),0)
    return {'rgb_peak_ev':float(np.log2(max(float(maximum.max()),1e-8))),
            'hdr_fraction':float(np.mean(maximum>1))}
