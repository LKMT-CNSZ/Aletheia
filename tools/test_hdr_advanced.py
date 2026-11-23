"""Selective color HDR, extended curve, SDR independence, persistence and UI."""
from pathlib import Path
import os,sys,tempfile,copy,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
import numpy as np
import core,hdr_color,hdr_advanced,desktop_model as model,calibration,hdr_io
from unittest.mock import patch
import native_app as ui

legacy=core.Params(mode='positive',black=0,white=1,hdr_enabled=True,hdr_strength=1.3,hdr_start=.3,hdr_softness=.75)
pixels=np.array([[[1.,.025,.5],[.1,.4,.9],[.02,.01,.015],[.5,.5,.5]]],np.float32)
old=hdr_color.grade(pixels,legacy)
p=copy.deepcopy(legacy);p.hdr_chroma=1;p.hdr_sky_protect=.8
new=hdr_color.grade(pixels,p)
assert new[0,0,0]>old[0,0,0]*1.3 # Saturated flower was missed by luma-only grading.
assert new[0,1,2]<old[0,1,2] # Blue protection doesn't brighten sky indiscriminately.
assert np.array_equal(new[0,2],pixels[0,2])
assert np.allclose(new[0,0]/new[0,0,0],pixels[0,0]/pixels[0,0,0])
p.hdr_target='red';selected=hdr_color.grade(pixels,p);assert np.allclose(selected[0,1],pixels[0,1])
assert not hdr_advanced.active(legacy)
assert calibration.parameter_signature(legacy.__dict__)==calibration.parameter_signature(p.__dict__)

ramp=np.repeat(np.geomspace(.0001,64,2000,dtype=np.float32)[None,:,None],3,axis=2)
assert hdr_advanced.curve(ramp,[[0.,0.],[1.,1.]]) is ramp
curve=[[0.,0.],[.165,.165],[.39,.49],[1.,1.]]
mapped=hdr_advanced.curve(ramp,core.normalize_curve(curve))
assert np.all(np.diff(mapped[0,:,0])>=0) and mapped.max()>1 and np.isfinite(mapped).all()
p.hdr_target='all';p.hdr_curve=curve
master=hdr_color.render(pixels,p)
q=copy.deepcopy(p);q.sdr_hdr_contrast=.3;q.sdr_hdr_highlights=-.3;q.sdr_hdr_saturation=-.4
assert np.array_equal(master,hdr_color.render(pixels,q))
assert not np.array_equal(hdr_color.sdr_rendition(master,p),hdr_color.sdr_rendition(master,q))
out=hdr_color.sdr_rendition(master,q);assert out.min()>=0 and out.max()<=1 and np.isfinite(out).all()
assert np.allclose(hdr_advanced.sdr_controls(np.zeros((1,1,3),np.float32),q),0)

folder=ROOT/'build/hdr-advanced-tests';folder.mkdir(parents=True,exist_ok=True)
app=ui.QApplication.instance() or ui.QApplication([])
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    root=Path(tmp);src=root/'source.tif';hdr_io.write(src,np.tile(pixels,(40,20,1)))
    model.open_image(src,input_mode='single',include_thumbnails=False)
    value=q.__dict__;recipe=model.recipe(value);assert recipe['version']==8
    from tiffread import read_tiff_linear
    import hdr_jxr,hdr_ultrahdr
    expected=model.hdr_edit_preview(value,full=True)['hdr_linear']
    model.export_hdr(root/'master.tif',value)
    assert np.allclose(read_tiff_linear(root/'master.tif'),expected,rtol=2e-6,atol=2e-6)
    model.export_hdr_view(root/'view.jxr',value)
    assert np.allclose(hdr_jxr.read_scrgb(root/'view.jxr')/(203/80),expected,atol=.002)
    model.export_ultrahdr(root/'gainmap.jpg',value)
    assert hdr_ultrahdr.codec().ultrahdr_check((root/'gainmap.jpg').read_bytes())
    assert model.recipe_params(recipe)==model.params(value).__dict__
    bad=copy.deepcopy(recipe);bad['version']=7
    try:model.recipe_params(bad)
    except ValueError:pass
    else:raise AssertionError('new recipe silently downgraded')
    project=root/'advanced.filmproj';model.save_project(project,value)
    data=model.read_project(project);assert data['version']==10 and data['frames']['0']['hdr_curve']==core.normalize_curve(curve)
    bad=copy.deepcopy(data);bad['version']=9;model.write_json(root/'bad.filmproj',bad)
    try:model.read_project(root/'bad.filmproj')
    except ValueError:pass
    else:raise AssertionError('new project silently downgraded')
    from batch_engine import sync_snapshot
    synced=sync_snapshot(data,data,value,['tone'],'absolute',0,0)
    assert synced['version']==10 and synced['frames']['0']['hdr_chroma']==1
    w=ui.MainWindow(root/'profile');w.show();errors=[];w.show_error=errors.append
    def idle():
        end=time.monotonic()+35
        while time.monotonic()<end:
            app.processEvents();time.sleep(.01)
            if w.job is None and not w.preview_timer.isActive() and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('UI timeout')
        assert not errors,errors
    w.open_project_path(str(project));idle();assert w.p['hdr_chroma']==1
    assert w.hdr_curve.isEnabled() and w.rows['sdr_hdr_contrast'].isEnabled()
    assert 'SDR' in w.hdr_feedback.text()
    w.edit_parameter('hdr_chroma',.4,True);idle();assert w.p['hdr_chroma']==.4
    w.travel(-1);idle();assert w.p['hdr_chroma']==1
    w.hdr_curve_changed([[0,0],[.5,.6],[1,1]]);idle();w.commit_history()
    assert w.p['hdr_curve'][1]==[.5,.6]
    # Use the app's language action so open widget text bindings update.
    w.language_actions['en'].trigger();app.processEvents()
    assert w.rows['hdr_chroma'].isEnabled()
    assert [w.tabs.tabText(i) for i in range(5)]==['Basic','Curves / HSL','Repair','Export','HDR']
    w.close();app.processEvents()
print('PASS selective color/dark protection/hue ratios, HDR curve, SDR-only controls, old defaults, v10/v8 gates, batch sync, UI controls/undo')
