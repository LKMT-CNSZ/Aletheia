"""Private-photo-free regressions for camera framing and safe base sampling."""
from pathlib import Path
import copy,os,sys,tempfile,time
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import strip,core,desktop_model as model,native_app as ui
from tiffio import write_tiff_rgb16

def camera_fixture():
    rng=np.random.default_rng(4626)
    a=np.full((600,900,3),.006,np.float32);base=np.array([.7,.3,.12],np.float32)
    a[15:585,100:750]=base
    a[30:570,230:720]=base*(.15+.5*rng.random((540,490,1)))
    a[240:330,230:720]=base*.75 # broad, bright image content, not a frame gap
    a[:,0:70]=base*.3 # incomplete neighbouring frame
    return a

image=camera_fixture()
for a in (image,np.rot90(image),np.repeat(np.repeat(image,3,axis=0),3,axis=1)):
    layout=strip.detect_layout(a)
    assert layout.kind=='window' and layout.frame_count==1
    assert layout.rotation==0 # film format cannot establish the subject's up direction
    _,_,x0,x1,y0,y1=strip.frame_boxes(layout)[0]
    assert (x1-x0)*(y1-y0)>.40*a.shape[0]*a.shape[1]
    assert (x1-x0)*(y1-y0)<.65*a.shape[0]*a.shape[1]

# A broad horizontal bright subject in an unframed image is not an inter-frame gap.
photo=np.full((1000,900,3),.25,np.float32);photo[440:560]=.8
assert strip.detect_layout(photo).kind=='single'
photo[440:560] = .25
photo[495:505] = .8
assert strip.detect_layout(photo).kind=='single'
assert strip.detect_layout(np.full((300,400,3),.4,np.float32)).kind=='single'

# The frames are bounded by the actual clear seam, even when the seam is
# thinner than the former cutoff or the input has no complete end frames.
roll = np.full((1590, 433, 3), .009, np.float32)
film_base = np.array([.72, .47, .33], np.float32)
roll_boxes = []
for left, right in ((17, 187), (250, 417)):
    roll[27:1563, left:right] = film_base
    for y0 in range(30, 30 + 6 * 255, 255):
        y1 = y0 + 248
        roll_boxes.append((left + 5, right - 5, y0, y1))
        roll[y0:y1, left + 5:right - 5] = film_base * np.linspace(
            .27, .53, right - left - 10, dtype=np.float32)[None, :, None]
    # This band is itself bright across the picture, but its width and
    # position disagree with the six regular physical frames.
    roll[614:670, left + 5:right - 5] = film_base

for candidate in (roll, roll.swapaxes(0, 1)):
    transposed = candidate is not roll
    layout = strip.detect_layout(candidate)
    assert layout.frame_count == 12 and layout.horizontal == transposed
    assert np.allclose(layout.bases, film_base)
    for index, ((_, _, x0, x1, y0, y1), expected) in enumerate(zip(strip.frame_boxes(layout), roll_boxes)):
        if transposed:
            x0, x1, y0, y1 = y0, y1, x0, x1
        left, right, top, bottom = expected
        assert left - 3 <= x0 <= left + 6 and right - 6 <= x1 <= right + 3, (index, x0, x1)
        assert top <= y0 <= top + 4 and bottom - 4 <= y1 <= bottom, (index, y0, y1)
    frames = strip.split_frames(candidate, layout)
    assert all(np.array_equal(data, strip.extract_one(candidate, layout, i)[2])
               for i, (_, _, data) in enumerate(frames))
partial = roll[162:1433, :]
assert strip.detect_layout(partial).frame_count == 8
assert strip.detect_layout(roll[::2, ::2]).frame_count == 12

# Backlight through the perforations and clipped red samples must not set
# the base for a photographed color negative. Its crop has no clear film.
orange=np.array([.82,.28,.12],np.float32)
perforated=np.full((320,480,3),.006,np.float32)
perforated[15:305]=orange
perforated[40:280,30:445]=orange*.30
for left in range(25,455,60):
    perforated[17:30,left:left+27]=1.
    perforated[291:304,left:left+27]=1.
perforated[31:37,32:440]=[1.,.34,.16]
for scan in (perforated,np.rot90(perforated)):
    assert np.allclose(strip.film_base_from_edges(scan),orange)
manual={'rotation':0,'frames':[{'id':'frame-0','box':[30,40,445,280]}]}
assert np.allclose(strip.manual_layout(perforated,manual).bases[0],orange)
manual['frames'][0]['base']=[.65,.24,.15]
assert strip.manual_layout(perforated,manual).bases[0]==[.65,.24,.15]
assert strip.film_base_from_edges(np.full_like(perforated,orange)) is None

# The legacy analysis used for old projects still reproduces its RAW grade.
from loader import Loaded
from dataclasses import replace

recoverable = perforated.copy()
recoverable[40:280,30:445] = np.linspace(.1,.9,415,dtype=np.float32)[None,:,None] * orange * [.8,.75,.48]
spec={'rotation':0,'frames':[{'id':'frame-0','box':[30,40,445,280]}]}
decoded = Loaded(recoverable,'scan.nef',480,320,True,working_space='prophoto')
info = model.engine.install_loaded(decoded.source,decoded,'strip',spec,auto_color=False)
grade = model.engine.STATE['params']
assert info['base']==orange.tolist() and grade.wb_gain[2] < .8
crop = recoverable[40:280,30:445]
neutral = replace(grade,wb_gain=[1.,1.,1.])
excess = core.scene_linear(crop,neutral)[0,200]
assert excess[2] > excess[1] and abs((excess * core.wb_gain(grade))[2] -
                                    (excess * core.wb_gain(grade))[1]) < abs(excess[2] - excess[1])
model.engine.install_loaded('scan.tif',replace(decoded,is_raw=False),'strip',spec,auto_color=False)
assert model.engine.STATE['params'].wb_gain == [1.,1.,1.]
assert model.default_working_space('scan.NEF') == 'prophoto'
assert model.default_working_space('scan.tif') == 'srgb'

app=ui.QApplication.instance() or ui.QApplication([])
(ROOT/'build/tests').mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT/'build/tests',prefix='detection-') as folder:
    folder=Path(folder);path=folder/'camera.tif';write_tiff_rgb16(path,image)
    opened=model.open_image(path)
    assert opened['info']['strip']['frames']==1
    region=model.source_region();assert region and region['box'][0]>220 and region['box'][2]<735
    # Auto mode in the layout editor must show the same one-window ROI as loading.
    dialog=ui.FrameLayoutDialog(model.layout_editor())
    dialog.mode.setCurrentIndex(dialog.mode.findData('single'))
    dialog.mode.setCurrentIndex(dialog.mode.findData('auto'))
    assert dialog.rows[0]['box']==region['box'];dialog.reject()
    project=folder/'auto.filmproj';model.save_project(project,opened['params'])
    restored=model.open_project(project);assert model.source_region()==region

    # Saved projects from the November automatic detector must reopen with
    # their longer fixed inset, even when the new estimator finds a better crop.
    nov_roll = np.full((1312, 430, 3), .006, np.float32)
    nov_roll[18:1288, 20:410] = film_base
    horizontal_tone = np.linspace(.3, .55, 372, dtype=np.float32)[None, :, None]
    for top in range(30, 30 + 4 * 319, 319):
        nov_roll[top:top + 287, 29:401] = film_base * horizontal_tone
    nov_source = folder/'november.tif'
    write_tiff_rgb16(nov_source, nov_roll)
    model.open_image(nov_source)
    decoded_nov = model.engine.STATE['native_loaded']
    new_geometry = model.layout_identity()
    previous = strip.detect_layout_previous(decoded_nov.linear)
    expected = [(0, 0, 20, 408, 62, 288), (0, 1, 20, 408, 376, 606),
                (0, 2, 20, 408, 694, 926), (0, 3, 20, 408, 1014, 1242)]
    assert strip.frame_boxes(previous) == expected
    model.engine.install_loaded(str(nov_source), decoded_nov, detected_layout=previous)
    old_geometry = model.layout_identity()
    assert old_geometry != new_geometry
    nov_project = folder/'november-film.filmproj'
    grade = copy.deepcopy(model.engine.STATE['params'].__dict__)
    grade['exposure'] = .21
    model.save_project(nov_project, grade)
    recovered = model.open_project(nov_project)
    assert model.layout_identity() == old_geometry and recovered['params']['exposure'] == .21

    # Old automatic layouts retain their exact boxes and per-frame processing.
    old_path=folder/'legacy-camera.tif'
    write_tiff_rgb16(old_path,image[np.arange(800)*600//800])
    model.open_image(old_path)
    ld=model.engine.STATE['native_loaded']
    model.engine.install_loaded(str(old_path),ld,legacy_detection=True)
    old_identity=model.layout_identity();assert old_identity!=model.read_project(project)['layout']
    assert old_identity is not None and model.engine.STATE['strip_layout'].frame_count>1
    old=model.engine.STATE['params'].__dict__;old['exposure']=.27
    old_project=folder/'old.filmproj';model.save_project(old_project,old)
    original_snapshot=model.read_project(old_project)
    model.open_image(path);model.open_project(old_project)
    assert model.layout_identity()==old_identity
    assert model.project_signature(model.project_snapshot(old))==model.project_signature(original_snapshot)
    saved_full=model.engine.STATE['full'];saved_params=model.clone(model.engine.STATE['params'].__dict__)
    damaged=copy.deepcopy(original_snapshot);damaged['layout']['rotation']=180
    model.write_json(folder/'damaged.filmproj',damaged)
    try:model.open_project(folder/'damaged.filmproj')
    except ValueError:pass
    else:raise AssertionError('damaged legacy layout accepted')
    assert model.engine.STATE['full'] is saved_full
    assert model.engine.STATE['params'].__dict__==saved_params

    # Endpoint validation reads original transmission and leaves failed edits intact.
    clipped=image.copy();clipped[100:160,300:360]=[1,.2,1]
    path2=folder/'endpoint.tif';write_tiff_rgb16(path2,clipped)
    opened=model.open_image(path2,input_mode='single');value=opened['params']
    before=copy.deepcopy(model.engine.STATE['params'].__dict__)
    try:model.sample(value,330/900,130/600,'base',True)
    except ValueError as error:assert '未应用' in str(error) and 'ProPhoto' in str(error)
    else:raise AssertionError('clipped base accepted')
    assert model.engine.STATE['params'].__dict__==before
    value=model.sample(value,150/900,.5,'base',True)
    assert not core.base_clipped_channels(value['base'])
    assert core.base_clipped_channels([1.,.2,0.])==[0,2]
    assert not core.base_clipped_channels([1.2,.4,.2]) # corrected illumination can exceed 1
    window=ui.MainWindow(folder/'profile');window.p=value;window.sync_ui()
    assert '解码端点' not in window.base_label.text()
    window.p['base']=[1.,.2,1.];window.sync_ui();assert '解码端点' in window.base_label.text()
    window.p['base']=[.7,.3,.12];window.sync_ui();assert '解码端点' not in window.base_label.text()
    window.loaded=False;window.close();app.processEvents()
print('PASS camera windows, horizontal strips, thin gaps, partial endpoints, source-pixel crops, auto project roundtrip, previous and legacy layout preservation, corrupt rollback, and clipped base protection')
