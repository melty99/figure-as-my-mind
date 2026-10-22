"""Immutable source/capture fingerprints, separate from display edits."""
import hashlib,json,copy,os,stat as stat_module,threading
from contextlib import contextmanager
from functools import wraps

def verified(operation):
 """Share successful checks only inside one synchronous read operation."""
 @wraps(operation)
 def run(self,*args,**kwargs):
  with self.integrity.batch():return operation(self,*args,**kwargs)
 return run
from pathlib import Path


# Python 3.10 on Windows exposes creation time as st_ctime. NTFS ChangeTime
# detects in-place edits even when size and LastWriteTime were restored.
if os.name=='nt':
 import ctypes
 from ctypes import wintypes
 class _BasicInfo(ctypes.Structure):
  _fields_=[('creation',ctypes.c_longlong),('access',ctypes.c_longlong),('write',ctypes.c_longlong),('change',ctypes.c_longlong),('attributes',wintypes.DWORD)]
 _kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 _kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];_kernel.CreateFileW.restype=wintypes.HANDLE
 _kernel.GetFileInformationByHandleEx.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];_kernel.GetFileInformationByHandleEx.restype=wintypes.BOOL
 _kernel.CloseHandle.argtypes=[wintypes.HANDLE];_kernel.CloseHandle.restype=wintypes.BOOL
 def _change_stamp(path):
  handle=_kernel.CreateFileW(str(path),0x80,7,None,3,0x80,None)
  if handle==ctypes.c_void_p(-1).value:return None
  try:
   info=_BasicInfo()
   return info.change if _kernel.GetFileInformationByHandleEx(handle,0,ctypes.byref(info),ctypes.sizeof(info)) else None
  finally:_kernel.CloseHandle(handle)
 # FileIdBothDirectoryInfo includes native ChangeTime and file identity.
 class _DirectoryInfo(ctypes.Structure):
  _fields_=[('next',wintypes.DWORD),('index',wintypes.DWORD),('creation',ctypes.c_longlong),('access',ctypes.c_longlong),('write',ctypes.c_longlong),('change',ctypes.c_longlong),('size',ctypes.c_longlong),('allocated',ctypes.c_longlong),('attributes',wintypes.DWORD),('nameLength',wintypes.DWORD),('eaSize',wintypes.DWORD),('shortLength',ctypes.c_byte),('shortName',wintypes.WCHAR*12),('fileId',ctypes.c_ulonglong),('name',wintypes.WCHAR*1)]
 def _directory_change_stamps(folder,wanted):
  handle=_kernel.CreateFileW(str(folder),1,7,None,3,0x02000000,None)
  if handle==ctypes.c_void_p(-1).value:return {}
  try:
   result={};buffer=ctypes.create_string_buffer(65536);kind=11
   for _ in range(4096):
    if not _kernel.GetFileInformationByHandleEx(handle,kind,buffer,len(buffer)):return result if ctypes.get_last_error()==18 else {}
    kind=10;offset=0
    while True:
     if offset+ctypes.sizeof(_DirectoryInfo)>len(buffer):return {}
     info=_DirectoryInfo.from_buffer(buffer,offset);length=info.nameLength
     if length%2 or offset+_DirectoryInfo.name.offset+length>len(buffer):return {}
     name=ctypes.wstring_at(ctypes.addressof(buffer)+offset+_DirectoryInfo.name.offset,length//2).casefold()
     if name in wanted:result[name]=(info.change,info.fileId,info.size,info.write)
     if not info.next:break
     if info.next%8 or info.next<_DirectoryInfo.name.offset+length:return {}
     offset+=info.next
    if wanted<=result.keys():return result
   return {}
  finally:_kernel.CloseHandle(handle)
else:
 def _change_stamp(path):return None
 def _directory_change_stamps(folder,wanted):return {}

class Integrity:
 def __init__(self,root):
  self.root=Path(root);self.path=self.root/'data-protection.json';self.checked={};self.resolved={};self.local=threading.local()
  self.entries=json.loads(self.path.read_text(encoding='utf-8'))['files'] if self.path.exists() else {}
  self.pin()
 def resolve(self,relative):
  path=(self.root/relative).resolve()
  if not path.is_relative_to(self.root) or Path(relative).parts[0] not in ('sources','figures'):raise ValueError('原数据保护路径不属于此项目')
  return path
 @contextmanager
 def batch(self):
  previous=getattr(self.local,'verified',None)
  self.verify()
  self.local.verified=set(self.entries) if previous is None else previous
  try:yield
  finally:self.local.verified=previous
 def verify(self,relative=None,force=False):
  names=list(dict.fromkeys(relative)) if isinstance(relative,(list,tuple,set)) else [relative] if relative else list(self.entries)
  scoped=getattr(self.local,'verified',None)
  if not force and scoped is not None and set(names)<=scoped:return True
  if self.path.exists():
   current=json.loads(self.path.read_text(encoding='utf-8'))['files']
   for name,entry in current.items():
    if name in self.entries and entry!=self.entries[name]:raise ValueError('原数据保护：校验记录被改写：'+name)
    self.entries.setdefault(name,entry)
  names=list(dict.fromkeys(relative)) if isinstance(relative,(list,tuple,set)) else [relative] if relative else list(self.entries)
  directories={};chains={};directory_files={};directory_changes={}
  # FindFirstFile supplies regular-file metadata on Windows without a separate
  # lstat for every source. Still query ChangeTime for every protected file.
  bulk={}
  if os.name=='nt':
   for name in names:bulk.setdefault(str((self.root/name).parent),set()).add(Path(name).name.casefold())
  def file_identity(path):
   parent=str(path.parent);wanted=bulk.get(parent,set())
   if len(wanted)<8:return os.lstat(path)
   if parent not in directory_files:
    with os.scandir(path.parent) as entries:
     directory_files[parent]={e.name.casefold():e.stat(follow_symlinks=False) for e in entries if e.name.casefold() in wanted}
   result=directory_files[parent].get(path.name.casefold())
   if result is None:raise FileNotFoundError(path)
   return result
  def directory_identity(folder):
   key=str(folder)
   if key not in directories:
    item=os.lstat(folder);flags=getattr(item,'st_file_attributes',0)
    # Child file writes change a normal directory's mtime but not its identity.
    # Reparse points additionally need mtime to detect retargeting.
    directories[key]=(item.st_dev,item.st_ino,item.st_ctime_ns,flags,getattr(item,'st_reparse_tag',0),item.st_mtime_ns if flags&0x400 else None)
   return directories[key]
  for name in names:
   if name not in self.entries:continue
   lexical=self.root/name
   try:
    own=file_identity(lexical);flags=getattr(own,'st_file_attributes',0)
    parent_key=str(lexical.parent)
    if parent_key not in chains:chains[parent_key]=tuple(directory_identity(folder) for folder in lexical.parents)
    parents=chains[parent_key]
    link=(own.st_dev,own.st_ino,own.st_ctime_ns,own.st_mtime_ns) if stat_module.S_ISLNK(own.st_mode) or flags&0x400 else None
    location=(parents,link)
    cached=self.resolved.get(name)
    if cached is None or cached[0]!=location:
     path=self.resolve(name);self.resolved[name]=(location,path)
    else:path=cached[1]
    item=os.stat(path) if link is not None else own
    if not stat_module.S_ISREG(item.st_mode):raise FileNotFoundError(name)
   except (FileNotFoundError,NotADirectoryError):raise ValueError('原数据保护：快照缺失，已停止操作：'+name)
   changed=None;native_identity=item.st_ino
   wanted=bulk.get(str(lexical.parent),set())
   if os.name=='nt' and link is None and path==lexical and len(wanted)>=8:
    parent=str(lexical.parent)
    if parent not in directory_changes:directory_changes[parent]=_directory_change_stamps(lexical.parent,wanted)
    entry=directory_changes[parent].get(lexical.name.casefold())
    # A replacement or concurrent write must fall back to an actual file
    # handle; never trust timestamps belonging to a different file version.
    # Python 3.10 DirEntry.stat reports st_ino=0 on Windows; the
    # native directory result supplies the actual file ID for the signature.
    if entry is not None and (not item.st_ino or entry[1]==item.st_ino) and entry[2]==item.st_size and (entry[3]-116444736000000000)*100==item.st_mtime_ns:changed=entry[0];native_identity=entry[1]
   if changed is None:changed=_change_stamp(path)
   signature=(item.st_size,item.st_mtime_ns,item.st_ctime_ns,native_identity,item.st_dev,changed)
   if not force and (os.name!='nt' or changed is not None) and self.checked.get(name)==signature:continue
   if hashlib.sha256(path.read_bytes()).hexdigest()!=self.entries[name]['sha256']:raise ValueError('原数据保护：发现来源/捕获被改写，已停止操作：'+name)
   self.checked[name]=signature
  if scoped is not None:scoped.update(names)
  return True
 def pin(self):
  self.verify();changed=False
  for folder in ('sources','figures'):
   # scandir-backed walking lists names without an extra Windows stat for every
   # already verified file. Still walk every directory and discover new inputs.
   for directory,dirs,files in os.walk(self.root/folder,followlinks=False):
    dirs[:]=[d for d in dirs if d!='__pycache__']
    prefix=Path(directory).relative_to(self.root).as_posix()+'/'
    for filename in files:
     if filename=='__pycache__':continue
     name=prefix+filename
     if name in self.entries:continue
     path=Path(directory)/filename
     if not path.is_file():continue
     self.resolve(name);self.entries[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size};changed=True
  if changed or not self.path.exists():
   from engine import atomic_json
   atomic_json(self.path,{'version':1,'policy':'immutable-originals-display-only-edits','files':self.entries})
 def report(self,state):
  self.verify(force=True);edits=[]
  for r in state['figures']:
   count=sum(bool(p.get('hidden') or p.get('mode')=='coordinates' or 'barValue' in p or any(p.get(k) for k in ('dx','dy'))) for p in r.get('native',{}).get('entities',{}).values())
   overlays=[{'object':key,'display':copy.deepcopy(p)} for key,p in r.get('overrides',{}).items() if p.get('hidden') or p.get('clipboardSource') or p.get('dataPolicy')=='display-copy-no-observations' or any(p.get(k) for k in ('tx','ty','sx','sy'))]
   if count or overlays:edits.append({'id':r['id'],'name':r['name'],'displayOnlyEdits':count,'entityDisplayOverrides':copy.deepcopy(r.get('native',{}).get('entities',{})),'svgDisplayOverrides':overlays})
  for group in state.get('groups',[]):
   for i,panel in enumerate(group.get('panels',[])):
    settings=panel.get('settings',{})
    if settings.get('native',{}).get('entities') or settings.get('overrides'):edits.append({'id':group['id'],'name':group['name'],'panel':i,'entityDisplayOverrides':copy.deepcopy(settings.get('native',{}).get('entities',{})),'svgDisplayOverrides':copy.deepcopy(settings.get('overrides',{}))})
  return {'protected':True,'verified':True,'fileCount':len(self.entries),'files':copy.deepcopy(self.entries),'displayEdits':edits,'statisticsInput':'original-captured-observations','hiddenPointsStillIncluded':True,'dataUpdates':'new-input-snapshot-explicit-recipe','note':'保护首次启用时登记当前快照；移动/隐藏和展示坐标保存在设置中。明确筛选和单位变换只生成新结果。'}
