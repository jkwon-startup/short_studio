"""Copy Codex/Claude output snapshots into short/YYYY-MM-DD/time_tool_ID.

Original runs/work and quality ledgers remain untouched. No credentials, API calls,
release operations, or recurring jobs. Paths are relative to this project's root.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,fcntl,hashlib,json,re,shutil,sys,tempfile,os

KST=ZoneInfo('Asia/Seoul')
MEDIA={'.mp4':'video','.mov':'video','.webm':'video','.mp3':'audio','.wav':'audio','.m4a':'audio','.flac':'audio','.ogg':'audio','.srt':'captions','.vtt':'captions','.png':'images','.jpg':'images','.jpeg':'images','.webp':'images'}
SKIP_DIRS={'segments','layers','previews','whisper','frames','decoded-frames','authored-stills','style-frames','source','source-v2','sources','fonts','manifests','node_modules','__pycache__'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def candidates(root,pid):
    run=root/'runs'/pid;work=root/'work'/pid
    found=[]
    for base in [run/'PROJECT',run/'AUDIO',run/'SCRIPT',run/'FINAL',work]:
        if not base.is_dir():continue
        for p in sorted(base.rglob('*')):
            if p.name in ('silent.mp4','concat.txt') or p.is_symlink() or not p.is_file() or any(x in SKIP_DIRS or x.startswith('.pending') for x in p.relative_to(base).parts[:-1]):continue
            if not p.resolve().is_relative_to(root.resolve()):continue
            ext=p.suffix.lower();group=MEDIA.get(ext)
            if group is None:
                if base==run/'SCRIPT' and ext in ('.json','.md','.txt'):group='script'
                elif p.name in ('script.json','tts_text.txt','tts_v1.txt','DIRECTION_CHANGED.md'):group='script'
                elif ext=='.zip' and p.name.startswith('editable'):group='source'
                elif p.parent==run/'PROJECT' and ext=='.md':group='notes'
                elif p.name in ('technical-measurements.json','partial-frame-review-current.json','design-packet.json'):group='notes'
            if group:found.append((p,group))
    return found

def has_audio_video(path):
    import subprocess
    r=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','csv=p=0',str(path)],capture_output=True,text=True)
    kinds=set(r.stdout.split())
    return {'video','audio'}<=kinds

def pick_final(outputs):
    """영상+음성이 함께 있는 완성 파일 중 FINAL > *_draft* > 최신 순으로 하나를 고른다."""
    vids=[p for p,g in outputs if g=='video' and has_audio_video(p)]
    if not vids:return None
    rank=lambda p:(('FINAL' in p.parts),('_draft' in p.name),p.stat().st_mtime)
    return max(vids,key=rank)

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def archive(root,pid,tool=None,when=None,status=None):
    root=Path(root).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',pid):raise ValueError('Invalid production ID')
    state=json.loads((root/'runs'/pid/'PROJECT/state.json').read_text())
    if state.get('mode')!='production':return {'id':pid,'status':'SKIPPED_NOT_PRODUCTION'}
    tool=tool or ('claude' if pid.startswith('claude-') else 'codex')
    if tool not in ('claude','codex'):raise ValueError('Invalid tool')
    outputs=candidates(root,pid)
    if not outputs:return {'id':pid,'status':'NO_OUTPUTS_YET'}
    moment=(when or datetime.now(KST)).astimezone(KST)
    short=root/'short'
    if short.is_symlink():raise ValueError('Storage root must be a real project directory')
    day=short/moment.strftime('%Y-%m-%d');day.mkdir(parents=True,exist_ok=True)
    pending=Path(tempfile.mkdtemp(prefix='.pending-'+tool+'-',dir=day))
    rows=[]
    try:
        for src,group in outputs:
            before=src.stat();digest=sha(src);after=src.stat()
            if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size):raise RuntimeError('Source changing: '+str(src.relative_to(root)))
            rel=Path(group)/src.name;dest=pending/rel
            if dest.exists():rel=Path(group)/(src.stem+'__'+digest[:10]+src.suffix);dest=pending/rel
            if not dest.exists():
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
            final=src.stat()
            if sha(dest)!=digest or sha(src)!=digest or (final.st_mtime_ns,final.st_size)!=(before.st_mtime_ns,before.st_size):raise RuntimeError('Source changed while copying: '+str(src.relative_to(root)))
            rows.append({'file':str(rel),'source':str(src.relative_to(root)),'sha256':digest,'bytes':before.st_size,'source_modified_at':datetime.fromtimestamp(before.st_mtime,KST).isoformat()})
        final_src=pick_final(outputs);final_name=None
        if final_src is not None:
            final_name='완성본'+final_src.suffix;shutil.copy2(final_src,pending/final_name)
        fingerprint=hashlib.sha256(json.dumps({'id':pid,'tool':tool,'files':rows,'status_snapshot':(status or {}).get('snapshot')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        # Reusing identical snapshots is safe; originals and older archives remain.
        for p in short.glob('*/*/manifest.json'):
            if p.parent.name.startswith('.'):continue
            prior=json.loads(p.read_text())
            if prior.get('fingerprint')==fingerprint:
                shutil.rmtree(pending) # Only this call's private, newly created copy.
                return {'id':pid,'status':'ALREADY_SAVED','path':str(p.parent),'files':len(rows)}
        folder=moment.strftime('%H-%M-%S')+'_'+tool+'_'+pid
        dest=day/folder
        if dest.exists():dest=day/(folder+'_'+pending.name.rsplit('-',1)[-1])
        manifest={'production_id':pid,'tool':tool,'brand':state.get('brief',{}).get('brand'),'topic':state.get('brief',{}).get('topic'),'stored_at':moment.isoformat(),'timezone':'Asia/Seoul','production_started_at':state.get('created'),'storage_kind':'COPY_OF_OUTPUTS_NOT_A_RELEASE','quality':'Archive creation does not approve quality. Original production status is recorded below.','production_status':status or {'scope':'Not evaluated here'},'fingerprint':fingerprint,'final_video':final_name,'final_source':str(final_src.relative_to(root)) if final_src else None,'files':rows}
        write_json(pending/'manifest.json',manifest)
        lines=[f'# {tool} · {pid}','',f'저장 시각: {moment:%Y-%m-%d %H:%M:%S} (한국시간)','', '원본 runs/work를 보존한 복사본입니다. 저장 자체는 대본 확정·품질 승인·FINAL 출고가 아닙니다.','',(f'**완성본(영상+음성): [{final_name}]({final_name})** ← 원본 {final_src.relative_to(root)}' if final_name else '완성본(영상+음성 합본) 없음: 렌더 전 단계'),'', '| 파일 | 원본 |','| --- | --- |']
        for r in rows:lines.append(f"| [{r['file']}]({r['file']}) | {r['source']} |")
        (pending/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        os.rename(pending,dest)
        return {'id':pid,'status':'SAVED','path':str(dest),'files':len(rows)}
    except BaseException as exc:
        # Failed copies stay hidden with evidence rather than appearing complete.
        write_json(pending/'storage-error.json',{'production_id':pid,'error':str(exc)})
        raise

def refresh_index(root):
    short=root/'short';short.mkdir(exist_ok=True)
    with (short/'.index.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        lines=['# 숏폼 제작물 모음','','한국시간의 저장 날짜·시간과 제작 도구별로 정리한 로컬 복사본입니다.','','| 저장 시각 | 도구 | 제작 ID | 완성본 | 파일 수 |','| --- | --- | --- | --- | --- |']
        for p in sorted(short.glob('*/*/manifest.json'),reverse=True):
            if p.parent.name.startswith('.'):continue
            m=json.loads(p.read_text());rel=p.parent.relative_to(short)
            fv=m.get('final_video');lines.append(f"| {m['stored_at']} | {m['tool']} | [{m['production_id']}]({rel}/README.md) | {f'[▶ {fv}]({rel}/{fv})' if fv else '-'} | {len(m['files'])} |")
        temp=short/'INDEX.md.tmp';temp.write_text('\n'.join(lines)+'\n',encoding='utf-8');os.replace(temp,short/'INDEX.md')

def main():
    ap=argparse.ArgumentParser(description='Codex/Claude 제작물 날짜·시간별 복사 저장')
    group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--id');group.add_argument('--all',action='store_true')
    ap.add_argument('--tool',choices=['codex','claude']);a=ap.parse_args()
    if a.all and a.tool:ap.error('--tool is for --id only')
    root=Path(__file__).resolve().parent.parent
    sys.path.insert(0,str(root))
    from studio.store import Store
    from studio.pipeline import status
    ids=[a.id] if a.id else sorted(p.parent.parent.name for p in (root/'runs').glob('*/PROJECT/state.json') if json.loads(p.read_text()).get('mode')=='production')
    result=[]
    for pid in ids:
        try:result.append(archive(root,pid,a.tool,status=status(Store(root,pid))))
        except Exception as exc:result.append({'id':pid,'status':'ERROR','reason':str(exc)})
    refresh_index(root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if any(r['status']=='ERROR' for r in result) else 0

if __name__=='__main__':raise SystemExit(main())
