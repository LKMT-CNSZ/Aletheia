"""Neutral anchors preserve linear luminance and bypass saturated colors."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

import core
import tone_balance


shadow = np.asarray([.095, .073, .046], dtype=np.float32)
light = np.asarray([.42, .64, .68], dtype=np.float32)
blue = np.asarray([.013, .15, .64], dtype=np.float32)
source = np.broadcast_to([shadow, light, blue], (260, 3, 3)).copy()
p = core.Params()
assert tone_balance.apply(source, p) is source
anchors = {zone: tone_balance.point(rgb, p.working_space)
           for zone, rgb in [('shadow', shadow), ('highlight', light)]}
p.tone_balance = tone_balance.normalize(anchors)
balanced = tone_balance.apply(source, p)
assert balanced.dtype == source.dtype
assert np.max(np.ptp(balanced[:, :2], axis=2)) < 1e-6
assert np.array_equal(balanced[:, 2], source[:, 2])
assert np.allclose(core.luma(balanced, p.working_space), core.luma(source, p.working_space), atol=1e-7)
assert np.array_equal(balanced[-1], balanced[0])
p.mode = 'bw_negative'
assert tone_balance.apply(source, p) is source

levels = np.linspace(.05, .85, 320, dtype=np.float32)[:, None, None]
cast = np.linspace([1.26, 1., .84], [.75, 1., 1.13], len(levels), dtype=np.float32)[:, None, :]
ramp = np.broadcast_to(levels * cast, (len(levels), 160, 3))
estimated = tone_balance.estimate(ramp, 'srgb')
assert set(estimated) == {'shadow', 'highlight'}, estimated
assert estimated['shadow'][1] < 0 < estimated['highlight'][1]
assert estimated['highlight'][3] < 0 < estimated['shadow'][3]
assert tone_balance.estimate(np.ones((100, 100, 3), dtype=np.float32), 'srgb') == {}
print('PASS tonal cast estimation, sampled neutrality, luminance and subject color')
