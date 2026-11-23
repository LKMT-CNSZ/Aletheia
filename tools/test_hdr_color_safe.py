"""Regression: preserve RGB ratios, clear all preset state and fit SDR gamut."""
from pathlib import Path
import os,sys,copy,time,tempfile,json
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
import numpy as np
import core,hdr_color,hdr_advanced,hdr_io,hdr_jxr,hdr_ultrahdr,desktop_model as model
import native_app as ui

colors=np.array([[[.9,.04,.45],[.1,.3,.8],[.15,.35,.07],[.55,.36,.25],[.18,.18,.18],[0,0,0],[.9,.9,.9]]],np.float32)
base=core.Params(mode='positive',black=0,white=1).__dict__
dirty=copy.deepcopy(base);dirty.update(hdr_punch=1,hdr_brilliance=1,sdr_hdr_contrast=.8,sdr_hdr_highlights=-.8,sdr_hdr_saturation=-.9,hdr_curve=[[0,0],[.5,.8],[1,1]])
style_keys={k for k in base if k.startswith(('hdr_','sdr_hdr_'))}
ratios=lambda x:x/np.maximum(x.sum(axis=-1,keepdims=True),1e-8)
errors={}
for name,settings in hdr_color.PRESETS.items():
    assert style_keys<=settings.keys(),name
    p=model.params(hdr_color.preset(dirty,name));clean=model.params(hdr_color.preset(base,name))
    assert p.hdr_punch==p.hdr_brilliance==p.sdr_hdr_contrast==p.sdr_hdr_highlights==p.sdr_hdr_saturation==0
    assert p.sdr_hdr_color_safe and p.hdr_curve==[[0.,0.],[1.,1.]]
    master=hdr_color.render(colors,p);sdr=hdr_color.sdr_rendition(master,p)
    assert np.array_equal(master,hdr_color.render(colors,clean))
    assert np.array_equal(sdr,hdr_color.sdr_rendition(master,clean))
    hdr_error=float(np.max(np.abs(ratios(master)-ratios(colors))))
    sdr_error=float(np.max(np.abs(ratios(sdr)-ratios(colors))))
    assert hdr_error<2e-6 and sdr_error<2e-6,(name,hdr_error,sdr_error)
    assert sdr.min()>=0 and sdr.max()<1 and np.isfinite(sdr).all()
    assert np.array_equal(master[0,5],colors[0,5])
    assert master[0,0].max()<4 # Saturated flower no longer forced into extreme radiance.
    errors[name]={'HDR_chromaticity_error':hdr_error,'SDR_chromaticity_error':sdr_error}
    q=copy.deepcopy(p);q.sdr_hdr_color_safe=False
    assert np.array_equal(master,hdr_color.render(colors,q))

value=hdr_color.preset(base,'bright');value['hdr_curve'][0][1]=.7
assert hdr_color.PRESETS['bright']['hdr_curve'][0][1]==0

folder=ROOT/'build/hdr-color-safe-tests';folder.mkdir(parents=True,exist_ok=True)
app=ui.QApplication.instance() or ui.QApplication([])
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    root=Path(tmp);src=root/'source.tif';hdr_io.write(src,np.tile(colors,(50,30,1)))
    model.open_image(src,input_mode='single',include_thumbnails=False)
    value=hdr_color.preset(dirty,'bright');recipe=model.recipe(value);assert recipe['version']==10
    assert model.recipe_params(recipe)==model.params(value).__dict__
    bad=copy.deepcopy(recipe);bad['version']=9
    try:model.recipe_params(bad)
    except ValueError:pass
    else:raise AssertionError('old recipe ignored color-safe mapping')
    dest=root/'color.filmproj';model.save_project(dest,value);snap=model.read_project(dest);assert snap['version']==12
    bad=copy.deepcopy(snap);bad['version']=11;model.write_json(root/'old.filmproj',bad)
    try:model.read_project(root/'old.filmproj')
    except ValueError:pass
    else:raise AssertionError('old project ignored color-safe mapping')
    from batch_engine import sync_snapshot
    synced=sync_snapshot(snap,snap,value,['tone'],'absolute',0,0)
    assert synced['version']==12 and synced['frames']['0']['sdr_hdr_color_safe']
    expected=model.hdr_edit_preview(value,full=True)['hdr_linear']
    model.export_hdr(root/'master.tif',value)
    from tiffread import read_tiff_linear
    assert np.allclose(read_tiff_linear(root/'master.tif'),expected,atol=2e-6)
    model.export_hdr_view(root/'view.jxr',value);assert np.allclose(hdr_jxr.read_scrgb(root/'view.jxr')/(203/80),expected,atol=.002)
    model.export_ultrahdr(root/'view.jpg',value);api=hdr_ultrahdr.codec();assert api.ultrahdr_check((root/'view.jpg').read_bytes())
    w=ui.MainWindow(root/'profile');w.show();ui_errors=[];w.show_error=ui_errors.append
    def idle():
        end=time.monotonic()+35
        while time.monotonic()<end:
            app.processEvents();time.sleep(.005)
            if w.job is None and not w.preview_timer.isActive() and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('color-safe UI timeout')
        assert not ui_errors,ui_errors
    w.open_project_path(str(dest));idle();assert w.sdr_color_safe.isChecked()
    w.sdr_color_safe.setChecked(False);idle();assert not w.p['sdr_hdr_color_safe']
    w.travel(-1);idle();assert w.p['sdr_hdr_color_safe']
    w.hdr_preset_buttons['impact'].click();idle();assert w.p['hdr_punch']==w.p['hdr_brilliance']==0
    w.language_actions['en'].trigger();app.processEvents();assert w.sdr_color_safe.text()=='Color-safe SDR mapping'
    w.close();app.processEvents()
(folder/'results.json').write_text(json.dumps({'status':'pass','preset_chromaticity':errors,'preset_state_leak':'fixed','HDR_master_unaffected_by_SDR_mapping':True,'v12_v10_batch_undo_exports':'pass'},indent=2),'utf-8')
print('PASS all five presets retain HDR/SDR RGB ratios, reset leaked style controls, deep-copy curves, smooth SDR gamut fit; v12/v10, batch, undo, real HDR exports and bilingual UI')
