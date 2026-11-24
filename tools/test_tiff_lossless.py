"""Bit-exact HDR/SDR TIFF compression, independent Deflate decode and UI routing."""
from pathlib import Path
import os,sys,tempfile,threading,struct,zlib,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
import numpy as np
import hdr_io,desktop_model as model,core,colorio
from tiffio import write_tiff_rgb16
from tiffread import read_tiff_linear,read_tiff
from tiff_formats import export_formats
from unittest.mock import patch
import native_app as ui

def fields(path):
    data=path.read_bytes();assert data[:2]==b'II'
    off=struct.unpack_from('<I',data,4)[0];n=struct.unpack_from('<H',data,off)[0];out={}
    for i in range(n):
        p=off+2+i*12;tag,kind,count=struct.unpack_from('<HHI',data,p);size={1:1,2:1,3:2,4:4,5:8,7:1}[kind]*count
        raw=data[p+8:p+12] if size<=4 else data[struct.unpack_from('<I',data,p+8)[0]:][:size]
        out[tag]=(kind,count,raw[:size])
    return data,out
def longs(tags,key):
    _,n,blob=tags[key];return struct.unpack('<'+'I'*n,blob)

app=ui.QApplication.instance() or ui.QApplication([])
folder=ROOT/'build/tiff-lossless-tests';folder.mkdir(parents=True,exist_ok=True)
sizes={}
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    root=Path(tmp)
    y,x=np.mgrid[:301,:137];image=np.stack([x/100+.05,y/90+.1,(x+y)/120+.3],axis=-1).astype(np.float32)
    image[0,0]=[-0.,np.nextafter(np.float32(0),np.float32(1)),32.125]
    for space in ('srgb','prophoto'):
        for shape in (image,image[:2,:3],image[:,::2]):
            for compression in ('none','deflate'):
                path=root/f'{space}-{shape.shape[0]}-{shape.shape[1]}-{compression}.tif'
                meta=hdr_io.write(path,shape,space,extra={'sample':'metadata retained'},compression=compression)
                actual=read_tiff_linear(path)
                assert np.array_equal(actual.view(np.uint32),shape.copy().view(np.uint32))
                assert hdr_io.metadata(path)==meta
                data,tags=fields(path);assert struct.unpack('<H',tags[259][2])[0]==(8 if compression=='deflate' else 1)
                assert struct.unpack('<3H',tags[258][2])==(32,32,32) and struct.unpack('<3H',tags[339][2])==(3,3,3)
                if compression=='deflate':
                    raw=b''.join(zlib.decompress(data[o:o+n]) for o,n in zip(longs(tags,273),longs(tags,279)))
                    assert raw==shape.astype('<f4').tobytes() # Independent strip decoder.
    assert hdr_io.tags(root/'srgb-301-137-deflate.tif')[278]<301
    for comp in ('none','deflate'):
        path=root/('zeros-'+comp+'.tif');hdr_io.write(path,np.zeros((350,300,3),np.float32),compression=comp);sizes[comp]=path.stat().st_size
    assert sizes['deflate']<sizes['none']/10
    event=threading.Event();event.set()
    try:hdr_io.write(root/'canceled.tif',image,cancel=event,compression='deflate')
    except InterruptedError:pass
    else:raise AssertionError('cancellation ignored')
    assert not (root/'canceled.tif').exists() and not list(root.glob('*.part'))
    class CancelLater:
        def __init__(self):self.n=0
        def is_set(self):self.n+=1;return self.n>=2
    try:hdr_io.write(root/'partial.tif',image,cancel=CancelLater(),compression='deflate')
    except InterruptedError:pass
    else:raise AssertionError('mid-write cancellation ignored')
    assert not (root/'partial.tif').exists() and not list(root.glob('*.part'))
    prior=root/'zeros-deflate.tif';original=prior.read_bytes()
    try:hdr_io.write(prior,image,compression='deflate')
    except FileExistsError:pass
    else:raise AssertionError('overwrote output')
    assert prior.read_bytes()==original
    try:hdr_io.write(root/'invalid.tif',image,compression='jpeg')
    except ValueError:pass
    else:raise AssertionError('invalid compression accepted')
    source=root/'srgb-301-137-deflate.tif';opened=model.open_image(source,input_mode='single',include_thumbnails=False)
    # The image loader's established nonnegative sanitation canonicalizes -0;
    # the TIFF reader and independent decoder above preserve every stored bit.
    assert np.array_equal(model.engine.STATE['full'],image)
    for comp in ('none','deflate'):write_tiff_rgb16(root/('sdr-'+comp+'.tif'),np.clip(image,0,1),compress=comp)
    assert np.array_equal(read_tiff(root/'sdr-none.tif'),read_tiff(root/'sdr-deflate.tif'))
    w=ui.MainWindow(root/'profile');w.show();errors=[];w.show_error=errors.append
    def idle():
        end=time.monotonic()+40
        while time.monotonic()<end:
            app.processEvents();time.sleep(.005)
            if w.job is None and not w.pending_command and not w.preview_timer.isActive() and not any(j.isRunning() for j in w.jobs):break
        else:raise AssertionError('TIFF export UI timeout')
        assert not errors,errors
    w.open_path(str(source));idle();value=dict(w.p,mode='positive',black=0,white=1);w.set_parameters(value);idle()
    formats=export_formats();assert len(formats)==5 and not any('Ultra HDR' in label or '.jxr' in label for label in formats)
    for label,(hdr,compression) in formats.items():
        if compression is None:continue
        dest=root/(f'ui-{hdr}-{compression}.jpg')
        with patch.object(ui.QFileDialog,'getSaveFileName',return_value=(str(dest),label)) as save:
            w.export_dialog();idle();assert save.call_args.args[3].split(';;')==list(formats)
        dest=dest.with_suffix('.tif');_,tags=fields(dest)
        assert struct.unpack('<H',tags[259][2])[0]==(8 if compression=='deflate' else 1)
        assert struct.unpack('<3H',tags[258][2])==((32,)*3 if hdr else (16,)*3)
        assert not Path(str(dest)+'.json').exists()
        assert w.progress.maximum()==read_tiff_linear(dest).shape[0]
        assert w.progress.value()==w.progress.maximum()
        if hdr:assert 'recipe' not in hdr_io.metadata(dest)
    assert np.array_equal(read_tiff_linear(root/'ui-True-none.tif').view(np.uint32),read_tiff_linear(root/'ui-True-deflate.tif').view(np.uint32))
    assert np.array_equal(read_tiff(root/'ui-False-none.tif'),read_tiff(root/'ui-False-deflate.tif'))
    w.photo_export_format.setCurrentIndex(w.photo_export_format.findData('both'))
    hdr_pair=root/'hdr-pair.tif'
    w.hdr_export_to(str(hdr_pair));idle()
    assert np.array_equal(read_tiff_linear(hdr_pair),read_tiff_linear(root/'ui-True-deflate.tif'))
    from PIL import Image
    with Image.open(hdr_pair.with_suffix('.jpg')) as jpg:
        assert jpg.format=='JPEG' and jpg.info.get('icc_profile')
    jpeg_filter=next(label for label,pair in formats.items() if pair==(False,None))
    with patch.object(ui.QFileDialog,'getSaveFileName',return_value=(str(root/'standalone.tif'),jpeg_filter)):
        w.export_dialog();idle()
    with Image.open(root/'standalone.jpg') as jpg:
        assert jpg.format=='JPEG' and jpg.size==(image.shape[1],image.shape[0])
        assert jpg.info['icc_profile']==colorio.icc_profile('srgb')
    assert not (root/'standalone.tif').exists()
    w.photo_export_format.setCurrentIndex(w.photo_export_format.findData('jpeg'))
    with patch.object(ui.QFileDialog,'getSaveFileName',return_value=('',jpeg_filter)) as save:
        w.export_dialog();assert save.call_args.args[4]==jpeg_filter and save.call_args.args[2].endswith('.jpg')
    w.photo_export_format.setCurrentIndex(w.photo_export_format.findData('tiff'))
    default=next(label for label,pair in formats.items() if pair==(True,'deflate'))
    w.settings.setValue('tiffCompression','deflate');w.hdr_canvas.active=True
    try:
        with patch.object(ui.QFileDialog,'getSaveFileName',return_value=('',default)) as save:
            w.export_dialog();assert save.call_args.args[4]==default and save.call_args.args[2].endswith('-hdr.tif')
    finally:w.hdr_canvas.active=False
    w.language_actions['en'].trigger();app.processEvents();english=export_formats()
    assert all('无损' not in label and '压缩' not in label for label in english)
    selected=next(label for label,pair in english.items() if pair==(True,'deflate'))
    with patch.object(ui.QFileDialog,'getSaveFileName',return_value=(str(root/'english.tif'),selected)):
        w.hdr_export_dialog();idle()
    assert hdr_io.tags(root/'english.tif')[259]==8
    w.close();app.processEvents()
(folder/'results.json').write_text(json.dumps({'status':'pass','float32_bytes_exact':True,'independent_deflate_decode':True,'single_multi_strip_noncontiguous':True,'srgb_prophoto_metadata':True,'HDR_values_and_reload':True,'SDR_16bit_exact':True,'cancel_no_overwrite':True,'TIFF_and_JPEG_filters_and_bilingual':True,'compressible_fixture_bytes':sizes},indent=2),'utf-8')
print('PASS lossless float32/16-bit TIFF, full-size sRGB JPEG-only and HDR companion exports, cancel and bilingual routing')
