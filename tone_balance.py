"""Luminance-dependent neutral balance for color negatives."""
import numpy as np


def normalize(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    density = value.get('density')
    if isinstance(density, (list, tuple)) and len(density) == 2:
        try:
            dens = np.asarray(density, dtype=np.float32)
        except (ValueError, TypeError, OverflowError):
            dens = np.empty(0)
        if dens.shape == (2, 3) and np.isfinite(dens).all():
            result['density'] = [np.clip(dens[0], -.8, 1.5).tolist(),
                                 np.clip(dens[1], .18, 3.).tolist()]
    for zone in ('shadow', 'highlight'):
        try:
            point = np.asarray(value.get(zone), dtype=np.float32)
        except (ValueError, TypeError):
            continue
        if point.shape == (4,) and np.isfinite(point).all() and .008 <= point[0] <= 1:
            result[zone] = [float(point[0]), *np.clip(point[1:], -.55, .55).tolist()]
    return result


def point(rgb, space, strength=1.):
    from core import luma

    level = float(luma(rgb, space))
    if not np.isfinite(rgb).all() or min(rgb) <= .006 or max(rgb) >= .995 or not .009 <= level <= .98:
        raise ValueError('取样点太暗或已剪裁，请选择有细节的灰白区域')
    adjustment = np.clip(np.log(level / rgb) * strength, -.55, .55)
    return [level, *adjustment.tolist()]


def estimate(rgb, space, imported=False):
    """Use abundant low-chroma samples and abstain on weak evidence."""
    from core import luma

    h, w = rgb.shape[:2]
    dy, dx = h // 20, w // 20
    sample = rgb[dy:h-dy:max(1,h//350), dx:w-dx:max(1,w//350)]
    luminance = luma(sample, space)
    maximum = sample.max(axis=2)
    minimum = sample.min(axis=2)
    clean = (minimum>.009) & (maximum<.98) & (maximum-minimum<.48*maximum)
    result = {}
    for zone, ranks in (('shadow', (.10,.32)), ('highlight', (.80,.95))):
        if imported and zone=='highlight':
            ranks=(.84,.97)
        low, high = np.quantile(luminance,ranks)
        usable = (luminance>=low) & (luminance<=high) & clean
        if np.count_nonzero(usable) < max(64, luminance.size*.025):
            continue
        pixels = sample[usable]
        log = np.log(pixels[:,[0,2]] / pixels[:,1:2])
        quartiles = np.quantile(log,[.25,.75],axis=0)
        if np.max(quartiles[1]-quartiles[0]) > .48:
            continue
        anchor = point(np.median(pixels,axis=0),space,.90 if imported else .80)
        if max(abs(v) for v in anchor[1:]) >= (.045 if imported else .06):
            result[zone]=anchor
    return result


def fit_import(rgb, p, camera=False):
    """Fit the working density ranges on a bounded sample of an orange-masked frame."""
    from dataclasses import replace
    from core import base_clipped_channels, luma, scene_linear, to_density, working_linear
    import metering

    if p.mode != 'color_negative' or p.scene_hdr or p.base is None or base_clipped_channels(p.base):
        return p
    red, green, blue = p.base
    if green > red*.92 or blue > green*.79:
        return p
    step = max(1, int(np.ceil(max(rgb.shape[:2])/440)))
    rgb = metering.region(rgb[::step,::step], p.meter_mode)
    h,w = rgb.shape[:2]
    if min(h,w) < 36:
        return p
    sample = rgb[h//14:h-h//14, w//14:w-w//14]
    valid = (sample.min(axis=2)>4e-5) & (sample.max(axis=2)<.995)
    if camera:
        center = rgb[h//5:h-h//5,w//5:w-w//5,0]
        low,high = np.quantile(center,[.01,.99])
        valid &= (sample[...,0]>=.58*low) & (sample[...,0]<=1.22*high)
    pixels = sample[valid]
    if len(pixels)<max(1500, .60*valid.size):
        return p
    density = to_density(pixels)-to_density(np.asarray(p.base,np.float32))
    dark, high = np.quantile(density,[.025,.975],axis=0)
    widths = high-dark
    if widths.min()<.27 or widths.max()>3.1:
        return p
    proxy = np.median((density-dark)/widths,axis=1)
    lo, hi = np.quantile(proxy,[.84,.96])
    bright = (proxy>=lo) & (proxy<=hi)
    # Use one group of likely highlights for all channels. Reject an estimate
    # that comes only from one corner or mixes very different subject colors.
    spread = (density[bright]-dark)/widths
    if np.max(np.ptp(np.quantile(spread,[.25,.75],axis=0),axis=0))>.27:
        return p
    selected = np.zeros(valid.shape,dtype=bool)
    selected[valid] = bright
    rows = np.array_split(selected,3)
    tiles = [part for row in rows for part in np.array_split(row,3,axis=1)]
    if sum(np.mean(tile)>.022 for tile in tiles)<3:
        return p
    light = np.median(density[bright],axis=0)
    if np.min(light-dark)<.23:
        return p

    # Fit dye-channel contrast before the exponential inversion can clip a
    # channel. Leave density headroom above the common highlight estimate.
    gains = np.clip(.53/(light-dark),.18,3.)
    fitted = replace(p,span=1.16,wb_gain=[1.,1.,1.],
                     tone_balance={'density':[dark.tolist(),gains.tolist()]})
    linear = scene_linear(sample,fitted)
    y = luma(linear,p.working_space)[valid]
    black,white = np.quantile(y,[.045,.992])
    if white-black<.03:
        return p
    fitted = replace(fitted,black=float(black),white=float(white),exposure=.47,tone_rolloff=.33)
    # Keep excluded borders out of the second stage and leave clipped samples
    # out of the neutral fit as well.
    rendered = working_linear(sample,fitted)
    rendered[~valid]=0
    fitted.tone_balance.update(estimate(rendered,p.working_space,imported=True))
    return fitted.normalized()


def apply(rgb, p):
    anchors = p.tone_balance
    if p.mode != 'color_negative' or not ('shadow' in anchors or 'highlight' in anchors):
        return rgb
    from core import luma

    shadow = anchors.get('shadow', [.075,0.,0.,0.])
    highlight = anchors.get('highlight', [.75,0.,0.,0.])
    low = np.log(max(.009,min(shadow[0],highlight[0]-.015)))
    high = np.log(max(.024,highlight[0]))
    dark, light = np.asarray(shadow[1:],np.float32),np.asarray(highlight[1:],np.float32)
    output = np.empty_like(rgb)
    for top in range(0,len(rgb),128):
        block = rgb[top:top+128]
        y = luma(block,p.working_space)
        blend = np.clip((np.log(np.maximum(y,.009))-low)/(high-low),0,1)
        blend = blend*blend*(3-2*blend)
        gain = np.exp(dark + blend[...,None]*(light-dark))
        adjusted = block * gain
        maximum = adjusted.max(axis=2)
        saturation = (maximum-adjusted.min(axis=2))/np.maximum(maximum,1e-6)
        # Protect saturated subject colors in the same luminance range.
        weight=np.clip((.65-saturation)/.40,0,1)
        adjusted *= (y/np.maximum(luma(adjusted,p.working_space),1e-8))[...,None]
        output[top:top+128]=block+(adjusted-block)*weight[...,None]
    return output
