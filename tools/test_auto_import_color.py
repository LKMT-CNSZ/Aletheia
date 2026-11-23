"""A masked scan is corrected through the normal file-open entry point."""
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image

import core
import desktop_model as model

y,x = np.mgrid[:288,:384]
tone = .10 + .83 * np.mod(x,96)/95
base = np.array([.69,.32,.11],dtype=np.float32)
density = tone[...,None]*np.array([.88,.89,1.64],dtype=np.float32)
density[(y%96)>70] += [.065,-.055,.015]
negative = base*10**-density

with TemporaryDirectory() as directory:
    root=Path(directory)
    source=root/'scan.png'
    Image.fromarray((core.srgb_encode(negative)*255+.5).astype(np.uint8)).save(source)
    model.DOCUMENTS.set_budget(32*1024*1024)
    old=model.open_image(source,auto_color=False)['params']
    assert old['tone_balance']=={}
    original=model.preview(old)['pixels']
    fresh=model.open_image(source)['params']
    assert 'density' in fresh['tone_balance']
    corrected=model.preview(fresh)['pixels']
    # The old meter replaced the fitted density range with a raw-film span
    # while retaining black/white levels from the fit.
    assert abs(core.auto_anchor(model.engine.STATE['full'],fresh['base'],fresh['meter_mode'])[1]-fresh['span']) > .15
    remetered=model.meter(fresh)
    assert np.array_equal(model.preview(remetered)['pixels'],corrected)
    for key in ('exposure','span','black','white','tone_balance'):
        assert remetered[key]==fresh[key],key
    new_base=[v*scale for v,scale in zip(fresh['base'],(.96,1.08,1.03))]
    with patch.object(model.strip,'film_base_from_edges',return_value=new_base):
        measured=model.meter(fresh)
        assert np.allclose(measured['base'],new_base)
        assert measured['tone_balance']['density'][0]!=fresh['tone_balance']['density'][0]
        assert np.max(np.abs(model.preview(measured)['pixels'].astype(int)-corrected.astype(int)))<=1
        again=model.meter(measured)
        assert again==measured
    with patch.object(model.strip,'film_base_from_edges',return_value=[1.,1.,1.]):
        assert model.meter(fresh)['base']==fresh['base']
    area=np.s_[40:60,174:182]
    assert np.ptp(np.median(corrected[area],axis=(0,1))) < np.ptp(np.median(original[area],axis=(0,1)))*.35
    for name, values, version, expected in [('old',old,8,original),('new',fresh,14,corrected)]:
        project=root/(name+'.filmproj')
        model.save_project(project,values)
        assert model.read_project(project)['version']==version
        reopened=model.open_project(project)['params']
        assert np.array_equal(model.preview(reopened)['pixels'],expected)
    hits=model.DOCUMENTS.analysis_hits
    assert model.open_image(source)['params']==fresh
    assert model.DOCUMENTS.analysis_hits==hits+1
    assert model.recipe(fresh)['version']==12

    # Use the same source data as a RAW camera reproduction to exercise the
    # prior film-base and white-balance re-metering path.
    decoded=model.engine.STATE['native_loaded']
    bordered=decoded.linear.copy()
    bordered[:18]=bordered[-18:]=base
    camera=replace(decoded,linear=bordered,is_raw=True)
    model.engine.install_loaded(str(source),camera,'single')
    baseline=model.engine.STATE['params'].__dict__
    assert model.engine.STATE['info']['initial_negative_wb']==baseline['wb_gain']
    assert 'density' in baseline['tone_balance']
    moved={'mode':'strip','manual':{'rotation':0,'frames':[
        {'id':'frame-0','box':[5,23,190,265]},
        {'id':'frame-1','box':[197,23,379,265]},
    ]}}
    baseline=dict(baseline,exposure=.72)
    cut=model.reframe(moved,baseline)
    for key in ('base','span','black','white','wb_gain','tone_balance','exposure'):
        assert cut['params'][key]==baseline[key],key
    independent=model.engine.STATE['frame_params'][1]
    assert 'density' in independent['tone_balance']
    assert independent['tone_balance']['density']!=baseline['tone_balance']['density']
    assert independent['exposure']==baseline['exposure']
    assert model.restore_layout(cut['previous'])['params']==baseline

print('PASS import, stable re-metering, cached and saved grades, trim stability, independently metered added frame, and undo')
