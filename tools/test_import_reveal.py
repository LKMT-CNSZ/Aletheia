"""Soft reveal on opening/frame changes, interruption and immutable editing data."""
from pathlib import Path
import os,sys,time,tempfile,copy
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import native_app as ui
import native_import_reveal as reveal
from unittest.mock import patch
from tiffio import write_tiff_rgb16
from PySide6.QtCore import QEvent,QPointF,Qt
from PySide6.QtGui import QMouseEvent,QPainter,QImage,QPixmap
import numpy as np

a=np.full((12,60,3),30,np.uint8);b=np.full_like(a,210)
assert np.array_equal(reveal.mixed(a,b,0),a) and np.array_equal(reveal.mixed(a,b,1),b)
for progress in (.2,.5,.8):
    r=reveal.mixed(a,b,progress)
    assert np.array_equal(r[...,0],r[...,1]) and np.array_equal(r[...,1],r[...,2])
    assert np.all(np.diff(r[0,:,0].astype(int))<=0)
r=reveal.mixed(a,b,.5);assert np.all(r[:,:20]==210) and np.all(r[:,40:]==30) and 30<r[0,30,0]<210
assert np.all(a==30) and np.all(b==210)
assert reveal.mixed(a.astype('float32'),b.astype('float32')*3,.5).max()>1

app=ui.QApplication([]);folder=ROOT/'build/reveal-tests';folder.mkdir(parents=True,exist_ok=True)
# Paint the actual optimized Qt overlay and compare to the mathematical feather.
rng=np.random.default_rng(9);source=rng.integers(0,256,(48,160,3),dtype=np.uint8);target=255-source
item=reveal.SoftRevealItem(None);item.setPixmap(QPixmap.fromImage(ui.image_from_array(source)))
for p in (0,.15,.5,.85,1):
    image=QImage(160,48,QImage.Format.Format_RGB32);painter=QPainter(image)
    painter.drawImage(0,0,ui.image_from_array(target));item.progress=p;item.paint(painter,None);painter.end()
    pixels=np.frombuffer(image.bits(),np.uint8).reshape(48,image.bytesPerLine())[:,:160*4].reshape(48,160,4)[...,[2,1,0]]
    assert np.abs(pixels.astype(int)-reveal.mixed(source,target,p).astype(int)).max()<=3
with tempfile.TemporaryDirectory(dir=folder) as tmp,patch.object(reveal,'system_animations',return_value=True):
    root=Path(tmp);w=ui.MainWindow(root/'profile');w.show();errors=[];w.show_error=errors.append
    def idle():
        end=time.monotonic()+30
        while time.monotonic()<end:
            app.processEvents();time.sleep(.005)
            if w.job is None and not w.pending_command and not w.preview_timer.isActive() and not w.preview_pending and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('Preview timeout')
        assert not errors,errors
    y,x=np.mgrid[:80,:120];transmission=.12+.35*(x+y)/200
    sources=[]
    for name,base in [('orange',[1,.7,.4]),('blue',[.4,.7,1]),('red',[1,.4,.5])]:
        path=root/(name+'.tif');write_tiff_rgb16(path,transmission[...,None]*np.array(base,np.float32),with_icc=False);sources.append(path)
        before=w.import_reveal.starts;w.open_path(str(path));idle()
        assert w.import_reveal.active and w.import_reveal.starts==before+1
        pixels=w.canvas.pixels.copy();params=copy.deepcopy(w.p)
        w.import_reveal.tick(.5)
        assert np.array_equal(w.canvas.pixels,pixels) and w.p==params and w.import_reveal.overlay.isVisible()
        w.import_reveal.tick(1);assert not w.import_reveal.active and not w.import_reveal.overlay.isVisible()
    count=w.import_reveal.starts
    w.edit_parameter('exposure',.25,True);idle();assert w.import_reveal.starts==count
    w.open_path(str(sources[-1]));idle();assert not w.import_reveal.active and w.import_reveal.starts==count
    # Unvisited frames start negative; completion develops exactly one thumbnail.
    strip_path=root/'strip.tif';write_tiff_rgb16(strip_path,np.tile(transmission[...,None]*np.array([1,.7,.4]),(1,3,1)),with_icc=False)
    manual={'rotation':0,'frames':[{'id':'a','box':[0,0,120,80]},{'id':'b','box':[120,0,240,80]},{'id':'c','box':[240,0,360,80]}]}
    result=ui.model.open_image(strip_path,input_mode='strip',manual=manual);result['_new_import']=True;w.on_opened(result);idle()
    import io
    from PIL import Image
    raw_thumb=np.asarray(Image.open(io.BytesIO(ui.model.original_thumbnails()[0])))
    means=raw_thumb.mean(axis=(0,1));assert means[0]>means[1]>means[2]
    assert w.import_reveal.active;count=w.import_reveal.starts
    first=w.frames.item(0).icon().cacheKey();second=w.frames.item(1).icon().cacheKey()
    w.import_reveal.tick(1)
    assert w.frames.item(0).icon().cacheKey()!=first and w.frames.item(1).icon().cacheKey()==second
    w.go_frame(1);idle();assert w.import_reveal.active and w.import_reveal.starts==count+1
    w.import_reveal.tick(1);w.go_frame(0);idle();assert w.import_reveal.active and w.import_reveal.starts==count+2
    w.go_frame(0);idle();assert w.import_reveal.starts==count+2
    assert w.frame_reveal_key() in w.developed_frames
    # Keep 100% coordinates and animate only the same visible region.
    assert w.frame_reveal_key(1) in w.developed_frames
    w.full_resolution=True;w.request_preview();idle();count=w.import_reveal.starts
    w.go_frame(1);idle();assert w.import_reveal.active and w.import_reveal.starts==count+1 and w.canvas.region_mode
    assert w.import_reveal.original.shape==w.canvas.pixels.shape and w.full_resolution
    w.import_reveal.tick(1);count=w.import_reveal.starts
    roll_project=root/'roll.filmproj';ui.model.save_project(roll_project,w.p,w.project_options())
    w.open_project_path(str(roll_project));idle();assert w.import_reveal.starts==count and not w.import_reveal.active
    w.full_resolution=False;w.canvas.fit_mode=True

    # An existing profile only has completion hashes from before the fix.
    w.developed_frames={w.frame_reveal_key(i,legacy=True) for i in (0,1)}
    w.build_frames(w.frame_thumbs)
    assert all(w.frame_reveal_key(i) in w.developed_frames for i in (0,1))
    unchanged_key=w.frame_reveal_key(1)
    changed_key=w.frame_reveal_key(0)

    def expected_icon(jpeg):
        from native_widgets import monitor_image
        pix=QPixmap();pix.loadFromData(jpeg)
        display=QPixmap.fromImage(monitor_image(pix.toImage(),w.monitor_profile))
        return ui.photo_icon(display).pixmap(140,95).toImage()

    def shown_thumb(index):
        return w.frames.item(index).icon().pixmap(140,95).toImage()

    # Adjust a developed frame other than the one currently in the editor.
    # The new thumbnail must use its new positive render. The never-viewed
    # frame to its right stays masked, and applying geometry does not animate.
    w.open_frames();idle();dialog=w.frame_dialog
    dialog.frames.setCurrentRow(0);dialog.set_input_angle(1.5);dialog.apply_result();idle()
    assert w.import_reveal.starts==count and w.info['strip']['index']==1
    assert w.frame_reveal_key(1)==unchanged_key
    assert w.frame_reveal_key(0)!=changed_key and w.frame_reveal_key(0) in w.developed_frames
    assert shown_thumb(0)==expected_icon(w.frame_thumbs[0])
    assert shown_thumb(2)==expected_icon(ui.model.original_thumbnails()[2])
    assert not w.frame_is_developed(2)
    edited_project=root/'reframed.filmproj';w.save_project_to(str(edited_project));idle()
    w.open_project_path(str(edited_project));idle()
    assert shown_thumb(0)==expected_icon(w.frame_thumbs[0]) and not w.frame_is_developed(2)
    w.go_frame(0);idle();assert w.import_reveal.active and w.import_reveal.starts==count+1
    w.import_reveal.tick(1)

    # Recover unchanged positives from an rc8 profile that had already
    # switched to manual frames before updating and lost their thumbnails.
    w.open_path(str(ROOT/'samples'/'pro-strip-demo.tif'));idle();w.import_reveal.tick(1)
    w.go_frame(1);idle();w.import_reveal.tick(1)
    old_auto={w.frame_reveal_key(i,legacy=True) for i in (0,1)}
    previous=ui.model.layout_editor()
    rows=previous['frames'];rows[1]['angle']=.25
    prior_edit=ui.model.reframe({'mode':'strip','manual':{'rotation':previous['rotation'],'frames':rows}},w.p)
    w.developed_frames=old_auto
    w.on_opened(prior_edit);idle();w.import_reveal.tick(1)
    assert shown_thumb(0)==expected_icon(w.frame_thumbs[0]) and w.frame_is_developed(0)
    assert shown_thumb(2)==expected_icon(ui.model.original_thumbnails()[2]) and not w.frame_is_developed(2)

    # Original frame and transformed target have identical flip/crop coordinates.
    result=ui.model.open_image(sources[0]);result['params'].update(crop=[.1,.1,.9,.9],flip=True,rotation=90);result['_new_import']=True
    w.developed_frames.clear();w.settings.setValue('importRevealSeen',[]);w.on_opened(result);idle();assert w.import_reveal.active
    assert w.import_reveal.original.shape==w.import_reveal.target.shape
    event=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(30,30),QPointF(30,30),Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    app.sendEvent(w.canvas.viewport(),event);assert not w.import_reveal.active
    # Canceling before the first preview cannot arm a delayed animation later.
    result=ui.model.open_image(sources[0]);result['_new_import']=True;w.developed_frames.clear();w.settings.setValue('importRevealSeen',[]);w.on_opened(result)
    count=w.import_reveal.starts;w.edit_parameter('exposure',.1,True);idle();assert w.import_reveal.starts==count
    # Existing library snapshots, saved projects and restored sessions also replay.
    path=root/'library.tif';write_tiff_rgb16(path,transmission[...,None]*np.array([.4,.7,1]),with_icc=False)
    identifier=w.import_library_paths([str(path)])['ids'][0];w.open_library_asset(identifier);idle();assert w.import_reveal.active
    w.edit_parameter('exposure',.35,True);idle();edited=copy.deepcopy(w.p);count=w.import_reveal.starts
    w.open_library_asset(identifier);idle();assert not w.import_reveal.active and w.import_reveal.starts==count and w.p==edited
    project=root/'edited.filmproj';ui.model.save_project(project,w.p,w.project_options());count=w.import_reveal.starts
    w.open_project_path(str(project));idle();assert not w.import_reveal.active and w.import_reveal.starts==count and w.p==edited
    count=w.import_reveal.starts;w.restore_session();idle();assert not w.import_reveal.active and w.import_reveal.starts==count and w.p==edited
    count=w.import_reveal.starts
    result=ui.model.open_image(sources[0]);result['_new_import']=True;result['params']['mode']='positive';w.developed_frames.clear();w.settings.setValue('importRevealSeen',[]);w.on_opened(result);idle();assert w.import_reveal.starts==count
    # The user's bottom navigation also shows standalone photos, not just strips.
    ids=w.import_library_paths([str(sources[1]),str(sources[2])])['ids'];w.set_photo_batch(ids)
    w.go_photo(0);idle();assert w.import_reveal.active;w.import_reveal.tick(1);count=w.import_reveal.starts
    w.next_button.click();idle();assert w.current_photo_row()==1 and w.import_reveal.starts==count+1 and w.import_reveal.active
    w.import_reveal.tick(1);w.prev_button.click();idle();assert w.current_photo_row()==0 and w.import_reveal.starts==count+2 and w.import_reveal.active
    # A real thumbnail press/release must follow the same path as the buttons.
    point=w.photos.visualItemRect(w.photos.item(1)).center()
    for kind,buttons in ((QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)):
        app.sendEvent(w.photos.viewport(),QMouseEvent(kind,QPointF(point),QPointF(point),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier))
    idle();assert w.current_photo_row()==1 and w.import_reveal.active and w.import_reveal.starts==count+3
    w.set_photo_batch([])
    # HDR presentation uses float values without mutating or clipping the target.
    old=w.canvas.hdr_controller
    class HDR:
        active=True
        def set_linear(self,value):self.linear=value
    sink=HDR();w.canvas.hdr_controller=sink
    try:
        target=np.full((12,60,3),4.,np.float32);w.import_reveal.start(a,b,a.astype('float32')/255,target)
        w.import_reveal.tick(.5);assert sink.linear.max()==4 and np.all(target==4) and np.allclose(sink.linear[...,0],sink.linear[...,1])
        w.import_reveal.stop();assert sink.linear is target
    finally:w.canvas.hdr_controller=old
    # The normal 1400-pixel square preview must not silently skip the animation.
    square=np.zeros((1400,1400,3),np.uint8)
    w.import_reveal.start(square,square.copy());assert w.import_reveal.active;w.import_reveal.stop()
    large=np.zeros((1500,1500,3),np.uint8)
    w.import_reveal.start(large,large);assert not w.import_reveal.active
    # Old first-import history must no longer suppress repeat playback.
    w.settings.setValue('importRevealSeen',['old-identity']);w.import_reveal.arm('color_negative');assert w.import_reveal.pending
    w.import_reveal.cancel();w.import_reveal.arm('color_negative');assert w.import_reveal.pending
    w.import_reveal.arm('bw_negative');assert w.import_reveal.pending and w.import_reveal.duration==1.6
    w.toggle_import_reveal(False);w.import_reveal.arm('color_negative');assert not w.import_reveal.pending
    w.toggle_import_reveal(True)
    with patch.object(reveal,'system_animations',return_value=False):
        w.import_reveal.arm('color_negative');assert not w.import_reveal.pending
    w.open_library_asset(identifier);idle();w.import_reveal.tick(1)
    w.settings.sync();w.loaded=False;w.close();app.processEvents()
    # A fresh window/profile load must preserve per-frame completion records.
    w=ui.MainWindow(root/'profile');w.show_error=errors.append
    w.open_library_asset(identifier);idle();assert w.import_reveal.starts==0 and not w.import_reveal.active
    w.loaded=False;w.close();app.processEvents()
print('PASS negative-to-positive thumbnail completion, single-frame layout edits and legacy completion migration, repeated frame changes, 100% views, project reopen, SDR/HDR and animation preferences')
