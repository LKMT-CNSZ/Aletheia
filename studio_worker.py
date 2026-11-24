"""One isolated export task. Durable per-frame intents survive interruption."""
from pathlib import Path
import argparse
import json
import os
import sys
import traceback
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parent))
if (Path(__file__).resolve().parent.parent/'portable-layout.json').is_file():
    from film_invert_launcher import configure
    configure()
from studio_store import StudioStore,queue_lock,sha256,QueueBusy,engine_signature
from file_io import io_path,publish_new


def publish(stage,destination,expected):
    """Never replace an existing output, even during retry/recovery."""
    stage,destination=io_path(stage),io_path(destination)
    if destination.exists():
        if sha256(destination)!=expected:raise ValueError('已完成的输出被修改，已保留文件；请新建导出任务：'+str(destination))
        return
    if not stage.is_file() or sha256(stage)!=expected:raise ValueError('缺少或改动了导出暂存文件，请新建任务：'+str(stage))
    publish_new(stage,destination)


def recover_output(store,job,index,record,preferred=None,reserved=()):
    directory=Path(job['destination'])
    part=record.get('tiff') or record['jpeg']
    companion=record.get('jpeg') if 'tiff' in record else None
    stage=io_path(directory/part['stage'])
    if preferred is not None and record['state']=='prepared' and stage.is_file():
        from export_policy import available_name
        if sha256(stage)!=part['sha256']:
            raise ValueError('导出暂存文件已被修改：'+str(stage))
        # A hard link may have been published just before a POSIX worker stopped.
        final=io_path(directory/part['name'])
        if final.exists() and stage.samefile(final):
            stage.unlink()
        else:
            while True:
                part['name']=available_name(directory,preferred,reserved,jpeg=companion is not None)
                if companion is not None:
                    companion['name']=str(Path(part['name']).with_suffix('.jpg'))
                store.checkpoint(job['id'],index,record)
                try:
                    publish_new(stage,io_path(directory/part['name']))
                except FileExistsError:
                    continue
                break
    else:
        publish(stage,directory/part['name'],part['sha256'])
    if companion is not None:
        publish(directory/companion['stage'],directory/companion['name'],companion['sha256'])
    if 'recipe' in record:
        # A pre-update task may own a staged sidecar. Keep any published file.
        recipe=record['recipe']
        stage=io_path(directory/recipe['stage'])
        if recipe['stage'] == part['stage']+'.json' and stage.is_file() and sha256(stage)==recipe['sha256']:
            stage.unlink()
    if record['state']!='done':
        record['state']='done';store.checkpoint(job['id'],index,record)


def frame_parameters(snapshot,index):
    import core
    import desktop_model as model
    import strip
    engine=model.engine;layout=engine.STATE['strip_layout'];saved=snapshot['frames']
    if layout is None:return engine.STATE['full'],model.params(saved[str(snapshot['current_frame'])])
    si,_,array=strip.extract_one(engine.STATE['strip_img'],layout,index)
    if str(index) in saved:p=model.params(saved[str(index)])
    else:
        roll=snapshot.get('roll_params');p=model.params(roll or {'meter_mode':model.snapshot_meter_mode(snapshot)});p.base,p.anchor=layout.bases[si],None
        if (snapshot['options']['auto_meter'] or roll is None) and 'density' not in p.tone_balance:_,p.span=core.auto_anchor(array,p.base,p.meter_mode)
    p=engine.prepare_params(p,engine.STATE['strip_img'],layout,index)
    if str(index) not in saved and p.flat_mode=='strip':
        p.base=engine.strip_field(engine.STATE['strip_img'],layout,index)[1]
        if snapshot['options']['auto_meter'] and 'density' not in p.tone_balance:_,p.span=core.auto_anchor(engine.corrected_input(array,p),p.base,p.meter_mode)
    if str(index) not in saved and snapshot.get('roll_params') is None and snapshot.get('auto_color'):
        p=engine.initial_frame_color(array,p)
    p.output_space=saved[str(snapshot['current_frame'])].get('output_space','srgb')
    return array,p


def execute(store,identifier,progress=lambda *args:None):
    import desktop_model as model
    with queue_lock(store.folder):
        store.claim(identifier);job=store.get_job(identifier)
        try:
            if store.cancelled(identifier):store.status(identifier,'paused');return 'paused'
            snapshot=job['snapshot']
            current_engine=engine_signature()
            layout=Path(__file__).resolve().parent.parent/'portable-layout.json'
            compatibility=json.loads(layout.read_text('utf-8')) if layout.is_file() else {}
            saved_engine=snapshot.get('_queue_engine')
            is_hdr=any(p.get('hdr_enabled') for p in [*snapshot['frames'].values(),snapshot.get('roll_params') or {}])
            key='compatible_hdr_queue_engines' if is_hdr else 'compatible_queue_engines'
            previous=compatibility.get(key,{}).get(current_engine,[])
            if isinstance(previous,str):previous=[previous]
            if saved_engine not in (current_engine,*previous):
                raise ValueError('处理引擎或依赖版本已改变，请用当前软件新建导出任务')
            # Existing project loader verifies the source hash and frame layout.
            model.open_project(store.materialize(snapshot,'job-'+identifier))
            store.flatten_unstarted_export(job)
            from export_policy import names,photo_format
            options=snapshot.get('_export') or {}
            format=photo_format({'jpeg':snapshot.get('_export_jpeg'),**options})
            filenames=names(snapshot['source']['path'],job['indices'],options)
            reserved={name.casefold() for name in filenames}
            flat=snapshot.get('_flat_export',False)
            directory=io_path(job['destination']);directory.mkdir(parents=True,exist_ok=True)
            for number,index in enumerate(job['indices']):
                if store.cancelled(identifier):store.status(identifier,'paused');return 'paused'
                record=store.get_job(identifier)['outputs'].get(str(index))
                if record is None:
                    array,p=frame_parameters(snapshot,index)
                    name=filenames[number];final=directory/name
                    if not flat and final.exists():raise ValueError('目标文件已经存在，已保留文件；请新建任务：'+str(final))
                    stage=directory/('.pending-'+uuid.uuid4().hex+'.part')
                    primary='jpeg' if format=='jpeg' else 'tiff'
                    jpeg=stage.with_suffix('.jpg.part') if format=='both' else None
                    try:
                        model.export_image(stage,p.__dict__,array,staged_jpeg=jpeg,jpeg_only=primary=='jpeg')
                        record={'state':'prepared','frame':index+1,'params':p.__dict__,'source_region':model.source_region(index),
                            primary:{'stage':stage.name,'name':name}}
                        outputs={primary:stage}
                        if jpeg is not None:
                            record['jpeg']={'stage':jpeg.name,'name':str(Path(name).with_suffix('.jpg'))}
                            outputs['jpeg']=jpeg
                        for key,file in outputs.items():
                            with file.open('r+b') as stream:os.fsync(stream.fileno())
                            record[key]['sha256']=sha256(file)
                    except Exception:
                        stage.unlink(missing_ok=True)
                        if jpeg is not None:jpeg.unlink(missing_ok=True)
                        raise
                    store.checkpoint(identifier,index,record)
                preferred=filenames[number] if flat else None
                recover_output(store,job,index,record,preferred,reserved-{preferred.casefold()} if flat else ())
                progress(number+1,len(job['indices']),str(directory))
            store.status(identifier,'completed');return 'completed'
        except Exception as error:
            store.status(identifier,'failed',str(error));raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True);parser.add_argument('--job',required=True)
    args=parser.parse_args();store=StudioStore(args.profile)
    try:
        def progress(done,total,path):print(json.dumps({'done':done,'total':total}),flush=True)
        execute(store,args.job,progress);return 0
    except QueueBusy as error:
        print(str(error),file=sys.stderr);return 75
    except Exception:
        traceback.print_exc();return 1

if __name__=='__main__':raise SystemExit(main())
