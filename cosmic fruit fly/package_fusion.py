"""Deterministic local research archive. Does not upload to GitHub."""
from __future__ import annotations
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
from fly_movement import HERE,sha256
from render_fusion import sources


def package(video:Path,preview:Path,out:Path):
    result,_,_=sources()
    if sha256(video)!=json.loads((HERE/'fusion_demo'/'video_manifest.json').read_text())['sha256']:
        raise ValueError('video SHA-256 not verified by manifest')
    if not preview.is_file():raise FileNotFoundError(preview)
    media=HERE/'videos';media.mkdir(exist_ok=True)
    target=media/video.name
    if not target.exists() or sha256(target)!=sha256(video):shutil.copyfile(video,target)
    art=HERE/'assets'/'fusion_preview.png';shutil.copyfile(preview,art)
    root=HERE.parent
    files=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root)
        if any(z in ('__pycache__','.pytest_cache','seed_cache','hard_mode_verify') for z in rel.parts):continue
        if p.suffix not in ('.py','.md','.json','.jsonl','.png','.mp4'):continue
        files.append(p)
    assert root/'beastbox'/'dyn12.py' in files
    required=['cosmic fruit fly/fusion_hard_mode.py','cosmic fruit fly/render_fusion.py',
              'cosmic fruit fly/fusion_demo/runs.jsonl','cosmic fruit fly/fusion_demo/results.json',
              'cosmic fruit fly/fusion_demo/video_manifest.json','cosmic fruit fly/fusion_demo/analysis.json',
              'cosmic fruit fly/tests/test_fusion.py', 'cosmic fruit fly/tests/test_render_fusion.py',
              'cosmic fruit fly/data/DATA_LICENSE.md','cosmic fruit fly/videos/'+video.name]
    names=[p.relative_to(root).as_posix() for p in files]
    assert all(x in names for x in required)
    manifest={'package_class':'isolated executed simulation + real-derived anatomy + historical QPU summary + MOCK bio',
              'github_status':'SOURCE NOT YET PUSHED','source_branch':'experiment/cosmic-fruit-fly-closure-002',
              'sources':result['source_sha256'],'ledger_sha256':result['ledger_sha256'],
              'video_sha256':sha256(video),'preview_sha256':sha256(preview),
              'files':{p.relative_to(root).as_posix():sha256(p) for p in files}}
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:
            info=zipfile.ZipInfo(p.relative_to(root).as_posix(),(2026,9,20,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
        info=zipfile.ZipInfo('PACKAGE_SHA256_MANIFEST.json',(2026,9,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise RuntimeError('corrupt zip entry')
        assert set(names).issubset(z.namelist())
        for name,h in manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('entry SHA mismatch '+name)
    print(json.dumps({'zip':str(out),'sha256':sha256(out),'size':out.stat().st_size,
         'entries':len(files)+1,'video_sha256':sha256(video),'ledger_sha256':result['ledger_sha256']},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--video',type=Path,required=True)
    ap.add_argument('--preview',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();package(a.video,a.preview,a.out)
