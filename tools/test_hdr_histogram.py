"""Split HDR RGB count conservation, white boundary, master data and UI modes."""
from pathlib import Path
import os,sys,tempfile,time,copy,json
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
import numpy as np
import hdr_histogram as hist,hdr_io,desktop_model as model
import native_app as ui
from native_widgets import Histogram
from i18n import render,trf

white_above=np.nextafter(np.float32(1),np.float32(2))
v=np.array([0,.18,1,white_above,2,4,64,128],np.float32)
a=np.repeat(v[None,:,None],3,axis=2);before=a.copy();d=hist.build(a)
assert np.array_equal(before,a)
assert all(b.sum()==8 for b in d['bins']) and d['samples']==8
for b in d['bins']:
    assert b[:hist.SDR_BINS].sum()==3 and b[hist.SDR_BINS:].sum()==5
    assert b[hist.SDR_BINS-1]==1 # Exact reference white stays in SDR.
    assert b[hist.SDR_BINS]==1 # Smallest float above white enters HDR.
    assert b[-1]==2 # +6 and overflow remain counted.
assert d['peak_ev']==7 and d['overflow_fraction']==1/8 and d['hdr_fraction']==5/8
color=np.array([[[.2,2,8],[.8,.4,.1]]],np.float32);rgb=hist.build(color)['bins']
assert rgb[0][:256].sum()==2 and rgb[0][256:].sum()==0
assert rgb[1][256:].sum()==1 and rgb[2][256:].sum()==1
assert not np.array_equal(rgb[1],rgb[2])
bad=np.array([[[-.2,.1,.2],[np.nan,2,3],[1,np.inf,2]]],np.float32)
assert hist.build(bad)['samples']==1 and hist.build(bad)['invalid']==2
empty=hist.build(np.empty((0,0,3),np.float32));assert empty['samples']==0 and empty['peak_ev'] is None
assert np.all(np.diff(hist.positions())>0)
assert hist.positions()[255]<hist.SDR_SHARE<hist.positions()[256]

app=ui.QApplication.instance() or ui.QApplication([])
folder=ROOT/'build/hdr-histogram-tests';folder.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    root=Path(tmp);src=root/'HDR source.tif'
    hdr_io.write(src,np.tile(a,(48,20,1)))
    w=ui.MainWindow(root/'profile');w.resize(1300,900);w.show();errors=[];w.show_error=errors.append
    def idle():
        end=time.monotonic()+40
        while time.monotonic()<end:
            app.processEvents();time.sleep(.005)
            if w.job is None and not w.pending_command and not w.preview_timer.isActive() and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('histogram UI timeout')
        assert not errors,errors
    w.open_path(str(src));idle();assert not w.histogram.hdr_enabled
    p=copy.deepcopy(w.p);p.update(mode='positive',black=0.,white=1.,hdr_enabled=True,hdr_strength=0.,hdr_limit=6.)
    w.set_parameters(p);idle();assert w.histogram.hdr_enabled
    expected=hist.build(w.hdr_scope_linear)
    assert all(np.array_equal(x,y) for x,y in zip(w.histogram.hdr_data['bins'],expected['bins']))
    assert w.histogram.headroom is None # An SDR preview must not invent display capability.
    saved=[b.copy() for b in w.histogram.hdr_data['bins']]
    w.edit_parameter('sdr_hdr_exposure',.7,True);idle()
    assert all(np.array_equal(x,y) for x,y in zip(saved,w.histogram.hdr_data['bins']))
    w.sdr_compare.setChecked(True);idle();assert w.histogram.hdr_enabled
    assert all(np.array_equal(x,y) for x,y in zip(saved,w.histogram.hdr_data['bins']))
    w.original_action.trigger();idle();assert not w.histogram.hdr_enabled
    w.original_action.trigger();idle();assert w.histogram.hdr_enabled
    w.hdr_check.setChecked(False);idle();assert not w.histogram.hdr_enabled
    # Image reload must not reuse old bins or the previous HDR mode.
    from PIL import Image
    src2=root/'SDR.png';Image.fromarray(np.full((80,100,3),100,np.uint8)).save(src2)
    w.open_path(str(src2));idle();assert not w.histogram.hdr_enabled and w.histogram.hdr_data is None
    # Actual frame navigation: current-frame statistics must follow restored edits.
    w.open_path(str(ROOT/'samples/pro-strip-demo.tif'));idle()
    w.keep_check.setChecked(False);w.meter_check.setChecked(False)
    w.hdr_check.setChecked(True);idle();assert w.histogram.hdr_enabled
    w.go_frame(1);idle();assert not w.histogram.hdr_enabled
    w.go_frame(0);idle();assert w.histogram.hdr_enabled
    assert all(np.array_equal(x,y) for x,y in zip(w.histogram.hdr_data['bins'],hist.build(w.hdr_scope_linear)['bins']))
    # Exercise the native-HDR display ceiling state without requiring a physical HDR monitor.
    w.histogram.set_hdr_bins(d,True,2.5);assert w.histogram.headroom==2.5
    for width in (300,400,640):
        w.histogram.resize(width,180);assert not w.histogram.grab().isNull()
    w.language_actions['en'].trigger();app.processEvents()
    assert w.histogram.accessibleName()=='SDR / HDR split RGB histogram'
    assert 'Display headroom' in render(trf('HDR 主图统计 · 屏幕余量 +{0:.1f} EV',2.5))
    w.close();app.processEvents()
(folder/'results.json').write_text(json.dumps({'status':'pass','RGB_counts':True,'white_boundary':True,'EV_overflow':True,'SDR_controls_do_not_change_master_histogram':True,'original_and_HDR_toggle':True,'frame_switch':True,'new_source_clears_state':True,'bilingual':True,'native_HDR_capacity':'mocked, physical display not required'},indent=2),'utf-8')
print('PASS main SDR/HDR RGB histogram: count conservation, white boundary, +6 overflow, master data, SDR proof, mode/image/frame changes, display ceiling, narrow layouts and bilingual UI')
