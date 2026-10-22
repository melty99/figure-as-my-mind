"""Locate optional local packages without altering the user's Python environment."""
import json
import os
import sys
from pathlib import Path


_automatic_node=None
_node_probe=None

def _restore_node(driver):
    """Restore only our exact bundled executable, offline and atomically."""
    import hashlib,zipfile
    archive=driver/'node.exe.zip'
    if not archive.is_file():return False
    target=driver/'node.exe';stage=driver/('.node-restore-'+str(os.getpid())+'.tmp')
    try:
        with zipfile.ZipFile(archive) as package:
            if set(package.namelist())!={'node.exe','sha256.json'}:raise ValueError('Invalid bundled Node backup')
            expected=json.loads(package.read('sha256.json'))
            if not 0<package.getinfo('node.exe').file_size<=150*1024*1024:raise ValueError('Invalid bundled Node size')
            digest=hashlib.sha256();size=0
            with package.open('node.exe') as source,stage.open('wb') as output:
                for chunk in iter(lambda:source.read(1024*1024),b''):output.write(chunk);digest.update(chunk);size+=len(chunk)
                output.flush();os.fsync(output.fileno())
            if digest.hexdigest()!=expected['sha256'] or size!=expected['bytes']:raise ValueError('Bundled Node backup checksum mismatch')
        stage.replace(target);return True
    finally:
        if stage.exists():stage.unlink()

def _configure_node(runtime):
    """Compact installations may use a compatible system Node with an offline fallback."""
    global _automatic_node,_node_probe
    if os.name!='nt':return
    explicit=os.environ.get('PLAYWRIGHT_NODEJS_PATH')
    if explicit and explicit!=_automatic_node:return
    driver=runtime/'playwright/driver';bundled=driver/'node.exe'
    if bundled.is_file():
        if explicit==_automatic_node and explicit:os.environ.pop('PLAYWRIGHT_NODEJS_PATH',None)
        _automatic_node=None;return
    package=driver/'package/package.json'
    if not package.is_file():return
    import re,shutil,subprocess
    requirement=json.loads(package.read_text(encoding='utf-8')).get('engines',{}).get('node','')
    minimum=re.fullmatch(r'>=([0-9]+)(?:\.0(?:\.0)?)?',requirement)
    candidate=shutil.which('node')
    if minimum and candidate:
        try:
            path=Path(candidate).resolve();stat=path.stat();signature=(str(path),stat.st_mtime_ns,stat.st_size,int(minimum[1]))
            if not _node_probe or _node_probe[0]!=signature:
                version=subprocess.check_output([str(path),'--version'],text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW).strip()
                major=re.fullmatch(r'v([0-9]+)\.[0-9]+\.[0-9]+',version)
                _node_probe=(signature,bool(major and int(major[1])>=int(minimum[1])))
            if _node_probe[1]:
                os.environ['PLAYWRIGHT_NODEJS_PATH']=str(path);_automatic_node=str(path);return
        except (OSError,ValueError,subprocess.SubprocessError):pass
    if explicit==_automatic_node and explicit:os.environ.pop('PLAYWRIGHT_NODEJS_PATH',None)
    _automatic_node=None
    _restore_node(driver)


def activate():
    here = Path(__file__).resolve()
    candidates = [Path(os.environ['FAM_RUNTIME'])] if os.environ.get('FAM_RUNTIME') else []
    for parent in here.parents:
        candidates.extend([parent / '.runtime', parent / '.figure-runtime'])
    ref = here.parent.parent / 'runtime-location.json'
    if ref.exists():
        candidates.append(Path(json.loads(ref.read_text(encoding='utf-8'))['path']))
    candidates.append(Path.home() / '.agents' / 'figure-as-my-mind-runtime')
    for candidate in candidates:
        if candidate.is_dir():
            location=str(candidate)
            if not sys.path or sys.path[0]!=location:
                if location in sys.path:sys.path.remove(location)
                sys.path.insert(0, location)
            _configure_node(candidate)
            return candidate


activate()
