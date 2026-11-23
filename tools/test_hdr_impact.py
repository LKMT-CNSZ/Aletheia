"""Opt-in HDR radiance, perceptual brilliance, persisted presets and RGB plot."""
from pathlib import Path
import os,sys,copy,tempfile,time,json,importlib.util
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
import numpy as np
import core,hdr_color,hdr_advanced,hdr_io,hdr_jxr,hdr_ultrahdr,desktop_model as model
import native_app as ui
from native_histogram import Histogram
from hdr_histogram import build

pixels=np.array([[[.9,.04,.45],[.1,.3,.8],[.18,.18,.18],[0,0,0],[.9,.9,.9]]],np.float32)
base=core.Params(mode='positive',black=0,white=1).__dict__
# Archived rc3 values remain reproducible; current presets are tested separately
# for color preservation rather than maximum luminance.
legacy={
    'clear':dict(hdr_enabled=True,hdr_strength=1.3,hdr_start=.45,hdr_softness=.75,hdr_limit=3.,hdr_chroma=.85,hdr_sky_protect=.6),
    'bright':dict(hdr_enabled=True,hdr_strength=2.6,hdr_start=.25,hdr_softness=.55,hdr_limit=3.2,hdr_chroma=1.,hdr_sky_protect=.45,hdr_punch=.35,hdr_brilliance=.25),
    'impact':dict(hdr_enabled=True,hdr_strength=3.,hdr_start=.22,hdr_softness=.5,hdr_limit=3.7,hdr_chroma=1.,hdr_sky_protect=.35,hdr_punch=1.,hdr_brilliance=.5),
}
presets={name:model.params({**base,**value}) for name,value in legacy.items()}
renders={name:hdr_color.render(pixels,p) for name,p in presets.items()}
light={name:core.luma(rgb,'srgb') for name,rgb in renders.items()}
assert light['impact'][0,0]>light['bright'][0,0]>light['clear'][0,0]
assert light['impact'][0,0]>light['clear'][0,0]*4 and light['impact'][0,0]>1
for name,p in presets.items():
    rgb=renders[name];assert np.isfinite(rgb).all() and rgb.min()>=0 and rgb.max()<2.**p.hdr_limit
    assert np.array_equal(rgb[0,2:],pixels[0,2:]) is False # Bright neutral light changes.
    assert np.array_equal(rgb[0,2:4],pixels[0,2:4]) # Midgray and true black stay unchanged.
    q=copy.deepcopy(p);q.sdr_hdr_exposure=1;q.sdr_hdr_highlights=-1
    assert np.array_equal(rgb,hdr_color.render(pixels,q))
    assert core.process(pixels,p).max()<=1
plain=copy.deepcopy(presets['impact']);plain.hdr_brilliance=0
rgb=hdr_color.render(pixels,plain)
assert core.luma(renders['impact'],'srgb')[0,0]>core.luma(rgb,'srgb')[0,0]
assert not hdr_advanced.impact_active(core.Params())
# Neutral controls exactly match the previous preview, when available locally.
prior=ROOT/'dist/3.1.2-rc2-compat/FilmInvertNative/app/hdr_color.py'
if prior.exists():
    spec=importlib.util.spec_from_file_location('hdr_color_rc2',prior);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    p=core.Params(hdr_enabled=True);a=np.random.default_rng(4).random((25,30,3),dtype=np.float32)*3
    assert np.array_equal(hdr_color.render(a,p),old.render(a,p))

app=ui.QApplication.instance() or ui.QApplication([])
folder=ROOT/'build/hdr-impact-tests';folder.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    root=Path(tmp);src=root/'source.tif';hdr_io.write(src,np.tile(pixels,(50,30,1)))
    model.open_image(src,input_mode='single',include_thumbnails=False)
    value=presets['impact'].__dict__;recipe=model.recipe(value);assert recipe['version']==9
    assert model.recipe_params(recipe)==value
    bad=copy.deepcopy(recipe);bad['version']=8
    try:model.recipe_params(bad)
    except ValueError:pass
    else:raise AssertionError('old recipe accepted new radiance')
    dest=root/'edit.filmproj';model.save_project(dest,value);snap=model.read_project(dest)
    assert snap['version']==11 and snap['frames']['0']['hdr_punch']==1
    bad=copy.deepcopy(snap);bad['version']=10;model.write_json(root/'old.filmproj',bad)
    try:model.read_project(root/'old.filmproj')
    except ValueError:pass
    else:raise AssertionError('old project accepted new radiance')
    from batch_engine import sync_snapshot
    synced=sync_snapshot(snap,snap,value,['tone'],'absolute',0,0)
    assert synced['version']==11 and synced['frames']['0']['hdr_brilliance']==value['hdr_brilliance']
    expected=model.hdr_edit_preview(value,full=True)['hdr_linear']
    model.export_hdr(root/'master.tif',value)
    from tiffread import read_tiff_linear
    assert np.allclose(read_tiff_linear(root/'master.tif'),expected,atol=2e-6)
    model.export_hdr_view(root/'view.jxr',value)
    assert np.allclose(hdr_jxr.read_scrgb(root/'view.jxr')/(203/80),expected,atol=.003)
    model.export_ultrahdr(root/'view.jpg',value)
    data=(root/'view.jpg').read_bytes();api=hdr_ultrahdr.codec();assert api.ultrahdr_check(data)
    _,_,metadata=api.ultrahdr_decode_jpeg(data);assert metadata['hdr_capacity_max']>4
    w=ui.MainWindow(root/'profile');w.show();errors=[];w.show_error=errors.append
    def idle():
        end=time.monotonic()+35
        while time.monotonic()<end:
            app.processEvents();time.sleep(.005)
            if w.job is None and not w.preview_timer.isActive() and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('impact UI timeout')
        assert not errors,errors
    w.open_project_path(str(dest));idle();assert w.rows['hdr_punch'].isEnabled()
    w.hdr_preset_buttons['bright'].click();idle();assert w.p['hdr_punch']==0 and w.p['sdr_hdr_color_safe']
    w.hdr_preset_buttons['impact'].click();idle();assert w.p['hdr_punch']==0 and w.p['hdr_strength']==hdr_color.PRESETS['impact']['hdr_strength']
    w.travel(-1);idle();assert w.p['hdr_strength']==hdr_color.PRESETS['bright']['hdr_strength']
    hist=w.histogram;assert not hist.log_scale
    xs,linear=hist.curves();hist.set_scale(True);_,log=hist.curves()
    assert not np.array_equal(linear,log)
    hist.set_scale(False);hist.set_hdr_bins(build(expected),True,2.5)
    for width in (300,400,640):hist.resize(width,180);assert not hist.grab().isNull()
    w.language_actions['en'].trigger();app.processEvents();assert w.hdr_preset_buttons['impact'].text()=='Highlight lift'
    w.close();app.processEvents()
(folder/'results.json').write_text(json.dumps({'status':'pass','perceived_flower_luminance':{k:float(v[0,0]) for k,v in light.items()},'HDR_master_TIFF_JXR_gainmap':'pass','v11_v9_persistence_batch_undo':'pass','neutral_rc2_exact':'pass when baseline exists','physical_HDR_appearance':'requires user display review'},indent=2),'utf-8')
print('PASS Bright/Impact radiance and brilliance, shadow preservation, limiter, old output, project/recipe/batch/undo, real TIFF/JXR/Ultra HDR, linear/log RGB histogram and bilingual controls')
