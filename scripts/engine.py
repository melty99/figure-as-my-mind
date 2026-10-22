"""Project persistence, source capture, SVG editing and exact preview exports."""
import base64
import copy
import csv
import gzip
import hashlib
import io
import json
import math
import os
import pickle
import re
import runpy
import shutil
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
import bootstrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.text import Text
from PIL import Image
import templates
import adjustments
import semantics
from collections import OrderedDict

NS='http://www.w3.org/2000/svg'; XLINK='http://www.w3.org/1999/xlink'
ET.register_namespace('',NS); ET.register_namespace('xlink',XLINK)
DEFAULT_STYLE={'fontFamily':'Arial', 'fontSize':11, 'titleSize':15, 'labelSize':12,
               'tickSize':10, 'textColor':'#243742', 'background':'#ffffff',
               'lineWidth':1.2, 'grid':False, 'spines':True, 'width':6.4, 'height':4.8,
               'preserveOriginal':True,'edited':[],'transparent':True}
EDITABLE={'g','text','tspan','path','rect','circle','ellipse','line','polyline','polygon','use','image'}
SAFE_ATTRS={'fill','stroke','stroke-width','stroke-dasharray','stroke-linecap','opacity','fill-opacity',
            'stroke-opacity','font-size','font-family','font-weight','font-style','text-anchor','dominant-baseline','letter-spacing','word-spacing',
            'x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','width','height','d','points','visibility','display'}


def safe_name(value):
    return re.sub(r'[^\w.\-]+','_',str(value),flags=re.UNICODE).strip('._')[:90] or 'figure'


def atomic_json(path, value, *, serialized=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    raw=(serialized if serialized is not None else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)).encode('utf-8')
    if path.name.endswith('.json.gz'):raw=gzip.compress(raw,compresslevel=1,mtime=0)
    with temp.open('wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    for attempt in range(5):
        try:
            temp.replace(path)
            break
        except PermissionError as error:
            if os.name!='nt' or getattr(error,'winerror',None) not in (5,32,33) or attempt==4:raise
            time.sleep(.02*2**attempt)


def deep_merge(a,b):
    out=copy.deepcopy(a)
    for k,v in b.items():
        out[k]=deep_merge(out.get(k,{}) if isinstance(out.get(k),dict) else {},v) if isinstance(v,dict) else copy.deepcopy(v)
    return out


def resolve_panel(source,settings,*,_readonly=False):
    """A restored panel uses its captured baseline, independent of source edits."""
    if _readonly:
        source=dict(source)
        for key in ('style','native','overrides','affine'):
            if key in source:source[key]=copy.deepcopy(source[key])
    else:source=copy.deepcopy(source)
    if settings.get('originalBaseline'):
        source.update(style=deep_merge(DEFAULT_STYLE,source.get('baseline',{})),native={},overrides={})
        source.pop('affine',None)
    for key in ('entities','seriesMoves','fitLabels'):
        for gid,patch in settings.get('native',{}).get(key,{}).items():
            if patch.get('reset'):source.get('native',{}).get(key,{}).pop(gid,None)
            if key=='entities' and patch.get('resetData'):
                original=source.get('native',{}).get(key,{}).get(gid,{})
                source.setdefault('native',{}).setdefault(key,{})[gid]={k:v for k,v in original.items() if k.startswith('errorScale') or k=='errorStyle'}
            if key=='entities' and patch.get('errorStyle',{}).get('reset'):
                source.get('native',{}).get(key,{}).get(gid,{}).pop('errorStyle',None)
    for gid,parts in settings.get('native',{}).get('boxStyles',{}).items():
        for role,patch in parts.items():
            if patch.get('reset'):source.get('native',{}).get('boxStyles',{}).get(gid,{}).pop(role,None)
    for gid,patch in settings.get('overrides',{}).items():
        if patch.get('reset'):source.get('overrides',{}).pop(gid,None)
    if settings.get('native',{}).get('figureTitle',{}).get('reset'):source.get('native',{}).pop('figureTitle',None)
    for ai,patch in settings.get('native',{}).get('axes',{}).items():
        if patch.get('resetTitle'):
            original=source.get('native',{}).get('axes',{}).get(ai,{})
            for k in ('title','titlePad','titlePosition','titleStyles','titleLoc'):original.pop(k,None)
        for loc,t in patch.get('titles',{}).items():
            if t.get('reset'):source.get('native',{}).get('axes',{}).get(ai,{}).get('titles',{}).pop(loc,None)
    for key,value in settings.items():
        source[key]=deep_merge(source.get(key,{}) if isinstance(source.get(key),dict) else {},value) if isinstance(value,dict) else copy.deepcopy(value)
    return source


def clean_svg(text):
    if '<!ENTITY' in text.upper(): raise ValueError('SVG 不支持外部实体')
    root=ET.fromstring(text)
    if root.tag.split('}')[-1]!='svg': raise ValueError('文件不是 SVG')
    forbidden={'script','foreignObject','iframe','animate','set','animateTransform','animateMotion'}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split('}')[-1] in forbidden: parent.remove(child)
            elif child.tag.split('}')[-1]=='style' and any(s in (child.text or '').lower() for s in ('url(', '@import', 'javascript:', 'expression(', '</')):
                parent.remove(child)
        for key,value in list(parent.attrib.items()):
            lower=key.split('}')[-1].lower()
            if lower.startswith('on'): del parent.attrib[key]; continue
            if lower=='href' and not (value.startswith('#') or re.match(r'^data:image/(png|jpeg|webp|gif);base64,',value,re.I)):
                del parent.attrib[key]
            elif ('url(' in value.lower() and re.search(r'url\(\s*[\'"]?(?!#)',value,re.I)) or 'javascript:' in value.lower() or '@import' in value.lower():
                del parent.attrib[key]
    for i,node in enumerate(root.iter()):
        if node.tag.split('}')[-1] in EDITABLE and not node.get('id'): node.set('id',f'fam-e{i}')
    scope=root.get('data-fam-scope') or hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    root.set('data-fam-scope',scope)
    for node in root.iter():
        if node.tag.split('}')[-1]=='style' and node.text:
            rules=[]
            for selector,body in re.findall(r'([^{}]+)\{([^{}]*)\}',node.text):
                selectors=[]
                for part in selector.split(','):
                    part=part.strip()
                    if part.startswith('svg[data-fam-scope='): selectors.append(part)
                    elif part=='svg': selectors.append(f'svg[data-fam-scope="{scope}"]')
                    else:
                        if part.startswith('svg '): part=part[4:]
                        selectors.append(f'svg[data-fam-scope="{scope}"] '+part)
                rules.append(','.join(selectors)+'{'+body+'}')
            node.text='\n'.join(rules)
    if not root.get('viewBox'):
        def length(v):
            match=re.match(r'([\d.]+)(.*)',v or '480'); n=float(match[1]); unit=match[2].strip()
            return n*{'in':72,'cm':72/2.54,'mm':72/25.4,'px':.75,'pt':1,'':1}.get(unit,1)
        root.set('viewBox',f'0 0 {length(root.get("width"))} {length(root.get("height"))}')
    return root


def svg_string(root): return ET.tostring(root,encoding='unicode')


def set_css(node, values):
    style={}
    for part in node.get('style','').split(';'):
        if ':' in part:
            k,v=part.split(':',1); style[k.strip()]=v.strip()
    for k,v in values.items():
        if k in SAFE_ATTRS:
            if 'url(' in str(v).lower() or 'javascript:' in str(v).lower(): raise ValueError('样式值不允许外部引用')
            style[k]=str(v)
    node.set('style',';'.join(f'{k}:{v}' for k,v in style.items()))


def clipboard_fragment(identifier, text):
    """A pasted drawing is an isolated decoration, never a new observation."""
    if not isinstance(text,str) or len(text.encode('utf-8'))>4*1024*1024:
        raise ValueError('复制的图形过大，请减少所选对象')
    fragment=clean_svg(text)
    if sum(1 for _ in fragment.iter())>50000:raise ValueError('复制的图形对象过多')
    ids={node.get('id'):identifier+'-fragment-'+str(i) for i,node in enumerate(fragment.iter()) if node.get('id')}
    for node in fragment.iter():
        for key,value in list(node.attrib.items()):
            if key.startswith('data-'):
                del node.attrib[key];continue
            if key=='id':node.set(key,ids[value]);continue
            value=re.sub(r'url\(\s*[\'"]?#([^\s)\'"]+)[\'"]?\s*\)',lambda m:'url(#'+ids.get(m[1],identifier+'-missing')+')',value)
            if key.split('}')[-1]=='href' and value.startswith('#'):value='#'+ids.get(value[1:],identifier+'-missing')
            node.set(key,value)
        # Captures inline resolved styles. Discard sheets to prevent global CSS
        # leaking into other objects; local definitions remain usable.
    for parent in list(fragment.iter()):
        for node in list(parent):
            if node.tag.split('}')[-1] in ('style','metadata','title','desc'):parent.remove(node)
    wrapper=ET.Element(f'{{{NS}}}g',{'id':identifier,'data-fam-layer':'annotation','data-fam-owner':identifier,'data-fam-display-copy':'true'})
    wrapper.extend(list(fragment))
    return wrapper


def patch_svg(root,style,overrides):
    edited=set(style.get('edited',[])); apply_all=not style.get('preserveOriginal',True)
    # Native typography is already resolved before layout. Reapplying global
    # CSS here would overwrite per-label choices and installed glyph fallbacks.
    global_text=style.get('_backend')!='matplotlib'
    for node in root.iter():
        if node.tag.split('}')[-1] in ('text','tspan'):
            values={}
            if global_text and (apply_all or 'fontFamily' in edited): values['font-family']=style.get('fontFamily','Arial')
            if global_text and (apply_all or 'textColor' in edited): values['fill']=style.get('textColor','#243742')
            if global_text and 'fontWeight' in style and (apply_all or 'fontWeight' in edited):values['font-weight']=style['fontWeight']
            if global_text and 'fontStyle' in style and (apply_all or 'fontStyle' in edited):values['font-style']=style['fontStyle']
            if values: set_css(node,values)
            if style.get('svgFontSize') and (apply_all or 'svgFontSize' in edited): set_css(node,{'font-size':style['svgFontSize']})
            elif style.get('_backend')=='svg' and (apply_all or 'fontSize' in edited):set_css(node,{'font-size':style.get('fontSize',11)})
            if global_text and (apply_all or edited & {'fontFamily','fontSize','svgFontSize','fontWeight','fontStyle'}):
                node.attrib.pop('textLength',None);node.attrib.pop('lengthAdjust',None)
        elif style.get('_backend')=='svg' and node.tag.split('}')[-1] in ('path','line','polyline','rect','polygon') and (apply_all or 'lineWidth' in edited):
            if 'stroke' in node.get('style','') or node.get('stroke'): set_css(node,{'stroke-width':style.get('lineWidth',1.2)})
    for identifier,props in overrides.items():
        if props.get('create')=='svg-fragment':
            root.append(clipboard_fragment(identifier,props.get('svg','')))
        if props.get('create') in ('text','rect','line','circle','ellipse','polygon','path'):
            ET.SubElement(root,f'{{{NS}}}{props["create"]}',{'id':identifier})
    by_id={n.get('id'):n for n in root.iter() if n.get('id')}
    for identifier,props in overrides.items():
        node=by_id.get(identifier)
        if node is None: continue
        if 'gradientStops' in props and node.tag.split('}')[-1] in ('linearGradient','radialGradient'):
            adjustments.validate_svg_gradient(props['gradientStops'])
            for child in list(node):node.remove(child)
            for stop in props['gradientStops']:
                rgba=adjustments.colors.to_rgba(stop['color'],stop.get('alpha',1))
                ET.SubElement(node,f'{{{NS}}}stop',{'offset':str(stop['position']),'stop-color':adjustments.colors.to_hex(rgba),'stop-opacity':str(rgba[3])})
        if props.get('detachReference'):
            from vector_tools import detach
            node=detach(root,node)
        targets=[node]+list(node.iter())[1:] if node.tag.split('}')[-1]=='g' else [node]
        css=props.get('css',{})
        definitions={n for d in node.iter() if d.tag.split('}')[-1] in ('defs','clipPath','mask') for n in d.iter()}
        for target in targets:
            if target in definitions:continue
            tag=target.tag.split('}')[-1]
            filtered={k:v for k,v in css.items() if (not k.startswith('font-') or tag in ('text','tspan','g')) and (k!='opacity' or target is node)}
            set_css(target,filtered)
            if tag in ('text','tspan') and any(k.startswith('font-') for k in filtered):
                target.attrib.pop('textLength',None);target.attrib.pop('lengthAdjust',None)
        for key,value in props.get('attrs',{}).items():
            if key in SAFE_ATTRS: node.set(key,str(value))
        if 'text' in props:
            text_node=node if node.tag.split('}')[-1] in ('text','tspan') else next((n for n in node.iter() if n.tag.split('}')[-1] in ('text','tspan')),None)
            if text_node is not None:
                text_node.attrib.pop('textLength',None);text_node.attrib.pop('lengthAdjust',None)
                for child in list(text_node): text_node.remove(child)
                value=str(props['text']).replace('\r\n','\n').replace('\r','\n')
                if '\n' in value:
                    parents={child:parent for parent in root.iter() for child in parent};anchor=text_node
                    while anchor.get('x') is None and anchor in parents:anchor=parents[anchor]
                    x=anchor.get('x','0').split()[0];text_node.text=None;text_node.set('data-fam-multiline','true')
                    for i,line in enumerate(value.split('\n')):
                        span=ET.SubElement(text_node,f'{{{NS}}}tspan',{'x':x,'dy':'0' if i==0 else str(props.get('lineSpacing',1.2))+'em',f'{{http://www.w3.org/XML/1998/namespace}}space':'preserve'})
                        span.text=line
                else:
                    text_node.attrib.pop('data-fam-multiline',None);text_node.text=value
        if 'lineSpacing' in props:
            adjustments.finite(props['lineSpacing'],.2,5)
            for text in node.iter():
                spans=list(text.findall(f'{{{NS}}}tspan'))
                for index,span in enumerate(spans):span.set('dy','0' if index==0 else str(props['lineSpacing'])+'em')
        tx=float(props.get('tx',0)); ty=float(props.get('ty',0)); rot=float(props.get('rotate',0)); scale=float(props.get('scale',1))
        if tx or ty or rot or scale!=1:
            px=float(props.get('pivotX',0));py=float(props.get('pivotY',0))
            node.set('transform',f'translate({tx} {ty}) translate({px} {py}) rotate({rot}) scale({scale}) translate({-px} {-py}) '+node.get('transform',''))
        if props.get('hidden'): set_css(node,{'display':'none'})
    return root


def assign_ids(fig):
    from planar3d import promote_insets
    promote_insets(fig)
    fig.canvas.draw()
    for ai,ax in enumerate(fig.axes):
        ax.set_gid(f'fam-axis-{ai}')
        ax.title.set_gid(f'fam-a{ai}-title'); ax.xaxis.label.set_gid(f'fam-a{ai}-xlabel'); ax.yaxis.label.set_gid(f'fam-a{ai}-ylabel')
        if hasattr(ax,'zaxis'): ax.zaxis.label.set_gid(f'fam-a{ai}-zlabel')
        for name,spine in ax.spines.items(): spine.set_gid(f'fam-a{ai}-spine-{name}')
        for i,line in enumerate(ax.lines): line.set_gid(f'fam-a{ai}-line-{i}')
        for i,p in enumerate(ax.patches): p.set_gid(f'fam-a{ai}-patch-{i}')
        for i,c in enumerate(ax.collections): c.set_gid(f'fam-a{ai}-collection-{i}')
        for i,image in enumerate(ax.images): image.set_gid(f'fam-a{ai}-image-{i}')
        for i,t in enumerate(ax.texts): t.set_gid(f'fam-a{ai}-text-{i}')
        if ax.get_legend(): ax.get_legend().set_gid(f'fam-a{ai}-legend')
    for i,artist in enumerate(fig.findobj()):
        if isinstance(artist,Text) and not artist.get_gid(): artist.set_gid(f'fam-text-{i}')


def serialize_figure(fig):
    # Figure unpickling otherwise registers a new pyplot manager. Capturing a
    # snapshot must not create extra figures in the source script's namespace.
    manager=fig.canvas.manager;fig.canvas.manager=None
    try:return pickle.dumps(fig,pickle.HIGHEST_PROTOCOL)
    finally:fig.canvas.manager=manager


def dataset_columns(rows,names):
    columns=[]
    for name in names:
        nonempty=typed=finite=0
        for row in rows:
            value=row.get(name)
            if value is None or str(value).strip()=='':continue
            nonempty+=1
            try:number=float(value);typed+=1;finite+=int(math.isfinite(number))
            except (TypeError,ValueError):pass
        columns.append({'name':name,'numeric':typed>0 and typed==nonempty,'numericCount':finite,'missing':len(rows)-nonempty,'nonfinite':typed-finite})
    return columns

def batch_filter(rows,mapping,kind,policy='error'):
    """Explicit complete-case selection on this figure's mapped fields only."""
    if policy not in ('error','omit'):raise ValueError('未知缺失值处理方式')
    numeric=set(mapping.get('features',[])) if kind in ('pca','heatmap') else {mapping.get('y')}
    if kind in ('scatter','line','vk','bubble','scatter3d') and mapping.get('x'):numeric.add(mapping['x'])
    if kind=='scatter3d':numeric.add(mapping.get('z'))
    if kind in ('scatter','vk','bubble') and mapping.get('size'):numeric.add(mapping['size'])
    if kind=='bar' and mapping.get('error'):numeric.add(mapping['error'])
    if None in numeric or '' in numeric:raise ValueError('请选择需要映射的数值变量')
    categorical={v for v in (mapping.get('group') if kind in ('scatter','line','vk','bubble','scatter3d','box','violin','pca') else None,mapping.get('x') if kind in ('bar','pie') else None) if v}
    fields=numeric|categorical
    if any(any(name not in row for name in fields) for row in rows):raise ValueError('映射变量不在数据表中')
    excluded=[]
    for i,row in enumerate(rows):
        missing=any(row[n] is None or str(row[n]).strip()=='' for n in categorical)
        for n in numeric:
            try:missing=missing or not math.isfinite(float(row[n]))
            except (TypeError,ValueError):missing=True
        if missing:excluded.append(i)
    if excluded and policy=='error':raise ValueError(f'所选变量有 {len(excluded)} 行缺失或非有限值；请清洗数据，或明确选择“按每张图排除缺失行”')
    excluded_set=set(excluded);selected=[r for i,r in enumerate(rows) if i not in excluded_set]
    if not selected:raise ValueError('所选变量没有完整有效观测，未生成图件')
    return selected,excluded

from data_integrity import verified

class Project:
    def __init__(self, root):
        self._render_cache=OrderedDict()
        self._state_validated=False
        self._panel_cache=OrderedDict()
        self._view_family=None
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        for name in ('figures','sources','exports','runtime','history'): (self.root/name).mkdir(exist_ok=True)
        path=self.root/'project.fam.json'
        self.state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'version':1,'id':uuid.uuid4().hex,'name':'图随我意 · 新项目','figures':[], 'groups':[], 'datasets':[],
            'active':None,'revision':0,'created':time.strftime('%Y-%m-%dT%H:%M:%S')}
        self.copy_runtime()
        from sequential_compositions import ensure_panel_ids
        ensure_panel_ids(self.state)
        from data_integrity import Integrity
        self.integrity=Integrity(self.root)
        for dataset in self.state['datasets']:
            if dataset.get('columnsVersion')!=2:
                rows=json.loads((self.root/dataset['file']).read_text(encoding='utf-8'))
                dataset['columns']=dataset_columns(rows,[c['name'] for c in dataset['columns']]);dataset['columnsVersion']=2
        self.registry={f['id']:copy.deepcopy(f) for f in self.state['figures']}
        for record in self.state['figures']:
            if record['backend']=='matplotlib' and record.get('metadataVersion')!=2:
                fig=pickle.loads((self.root/record['cache']).read_bytes())
                record['axes'],record['baseline']=adjustments.describe(fig);record['metadataVersion']=2
                for key,value in record['baseline'].items():
                    if key not in record['style'].get('edited',[]) and record['style'].get('preserveOriginal',True):record['style'][key]=value
                plt.close(fig)
                self.registry[record['id']]=copy.deepcopy(record)
        # Records loaded from project.fam.json were valid when committed. Mark the
        # baseline validated so an incremental save only rechecks changed groups
        # and sources instead of resolving every composition in the project.
        self._state_validated=True

    def copy_runtime(self):
        for name in ('bootstrap.py','engine.py','templates.py','adjustments.py','semantics.py','interaction_geometry.py','geometry.py','research.py','fitting.py','distributions.py','variants.py','paper_templates.py','paper_catalog.json','basic_paper_templates.py','basic_paper_catalog.json','group_frames.py','scientific_templates.py','analysis_templates.py','map_templates.py','map_data/land.geojson','map_data/countries.geojson','map_data/manifest.json','network_layout.py','composition.py','legend_layout.py','language_export.py','vector_import.py','publication_design.py','extended_templates.py','design_references.json','productivity.py','matrix_layout.py','research_variants.py','advanced_templates.py','bridge.R','bridge_semantic.R','ggplot_bridge.R','ggplot_import.py','native_scene.py','bridge_native.R','fam_save_figure.m','fam_bridge.h','workflow_recipe.py','workflow_charts.py','workflow_native.R','workflow_graphics.py','workflow_tools.py','workflow_delivery.py','workflow_jobs.py','workflow_matrix.py','data_integrity.py','journal_codec.py','json_protocol.py','vector_tools.py','spatial.py','spatial_scene.py','spatial_camera.py','planar_workflow.py','planar3d.py','axis_ticks.py','editability.py','sequential_compositions.py','group_linking.py'):
            source=Path(__file__).parent/name; target=self.root/'runtime'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.resolve()!=target.resolve() and (not target.exists() or source.read_bytes()!=target.read_bytes()):shutil.copy2(source,target)
        runtime=bootstrap.activate()
        if runtime:
            path=self.root/'runtime-location.json';value={'path':str(runtime)}
            if not path.exists() or json.loads(path.read_text(encoding='utf-8'))!=value:atomic_json(path,value)

    @verified
    def save(self, state=None):
        self.integrity.verify()
        scope=None
        if state is not None:
            if state.get('id')!=self.state['id']: raise ValueError('项目 ID 不一致')
            if state.get('revision')!=self.state['revision']: raise ValueError('其他窗口已修改项目，请重新载入后编辑')
            # A view/layer/name change cannot alter figure records. Preserve its
            # persistence without repeatedly cloning and validating 81 sources.
            interface_keys={'active','name','ui'}
            same_content=all(state.get(k)==self.state.get(k) for k in set(state)|set(self.state) if k not in interface_keys)
            if same_content:
                if not self._state_validated or any(self.registry.get(f['id'])!=f for f in self.state['figures']):
                    self.validate_state(self.state)
                    self._state_validated=True
                if state==self.state:return self.state
                updated=dict(self.state)
                for key in interface_keys:
                    if key in state:updated[key]=copy.deepcopy(state[key])
                    else:updated.pop(key,None)
                self.state=updated
                return self.commit_settings(discover_sources=False)
            # Frontend can edit figures but cannot redirect source/cache paths.
            state=copy.deepcopy(state)
            from sequential_compositions import ensure_panel_ids
            ensure_panel_ids(state)
            existing=dict(self.registry);existing.update({f['id']:f for f in self.state['figures']})
            for f in state['figures']:
                if f['id'] not in existing: raise ValueError('新增图件请使用导入或模板接口')
                approved=existing[f['id']]
                if approved.get('sourceRevisions'):
                    version=next((v for v in approved['sourceRevisions'] if (v.get('cache') or v.get('svg'))==(f.get('cache') or f.get('svg'))),None)
                    if version is not None:approved={**approved,**version}
                    f['sourceRevisions']=copy.deepcopy(existing[f['id']]['sourceRevisions'])
                for key in ('cache','svg','source','provenance','backend','axes','baseline','metadataVersion','chartType'):
                    if key in approved and (key not in f or f[key]!=approved[key]):f[key]=copy.deepcopy(approved[key])
            state['datasets']=copy.deepcopy(self.state['datasets'])
            for group in state.get('groups',[]):
                if len(group.get('panels',[]))>100: raise ValueError('一张组图最多 100 个子图')
                for panel in group.get('panels',[]):
                    if panel.get('figure') not in existing: raise ValueError('组图引用了不存在的图件')
                    panel['settings']={k:v for k,v in panel.get('settings',{}).items() if k in ('style','native','overrides','affine','originalBaseline')}
            from group_frames import synchronize,guard_layout
            from sequential_compositions import changed_references,group_affected
            changed_groups,changed_figures=changed_references(state,self.state)
            # The first save after loading has no validated baseline; validate the
            # complete project once. Afterwards only the records whose presentation
            # differs can have become invalid, so untouched groups are not resolved.
            scope=None if not self._state_validated else (changed_groups,changed_figures)
            if scope:self.validate_state(state,changed_groups,changed_figures)
            else:self.validate_state(state)
            guard_layout(state,self.state)
            from group_linking import synchronize as link_series
            linked=link_series(self,state,self.state)
            if linked:state.setdefault('ui',{})['sequentialLinkReport']=linked
            synchronize(state,self.state)
            if scope:self.validate_state(state,changed_groups,changed_figures)
            else:self.validate_state(state)
            semantics.guard_state(self.state,state)
            if state==self.state:return self.state
            # Render changed native settings before committing: a failed setter or
            # invalid Newick string must never replace the last working project.
            current={f['id']:f for f in self.state['figures']}
            proposed={f['id']:f for f in state['figures']}
            candidates=[(f,current.get(f['id'],{})) for f in state['figures']
                        if f['id'] in changed_figures or f['id'] not in current]
            old_groups={g['id']:g for g in self.state.get('groups',[])}
            for group in state.get('groups',[]):
                if scope and not group_affected(group,changed_groups,changed_figures):continue
                old_panels=old_groups.get(group['id'],{}).get('panels',[])
                for index,panel in enumerate(group['panels']):
                    if not panel.get('settings',{}).get('native'):continue
                    old=next((p for p in old_panels if p.get('id')==panel['id']),None) if panel.get('id') else old_panels[index] if index<len(old_panels) else None
                    previous=resolve_panel(current[old['figure']],old.get('settings',{})) if old and old['figure'] in current else {}
                    candidates.append((resolve_panel(proposed[panel['figure']],panel['settings']),previous))
            for candidate,previous in candidates:
                if candidate['backend']=='matplotlib' and candidate.get('native')!=previous.get('native'):
                    self.render_figure(candidate)
                elif candidate['backend']=='svg' and candidate.get('native')!=previous.get('native'):self.render_figure(candidate)
            self.state=state
        self.validate_state(self.state, *(scope if scope else (None,None)))
        self._state_validated=True
        for f in self.state['figures']:
            if self.registry.get(f['id'])!=f:self.registry[f['id']]=copy.deepcopy(f)
        return self.commit_settings()

    def commit_settings(self,discover_sources=True):
        self.state['revision']+=1; self.state['modified']=time.strftime('%Y-%m-%dT%H:%M:%S')
        serialized=json.dumps(self.state,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        atomic_json(self.root/'project.fam.json',self.state,serialized=serialized)
        atomic_json(self.root/'settings.json',self.state,serialized=serialized)
        if self.state['revision']%10==1:
            atomic_json(self.root/'history'/f'revision-{self.state["revision"]:05d}.json.gz',self.state,serialized=serialized)
            old=sorted([*(self.root/'history').glob('revision-*.json'),*(self.root/'history').glob('revision-*.json.gz')],key=lambda p:int(p.name.split('-')[1].split('.')[0]))
            for path in old[:-30]: path.unlink()
        if discover_sources:self.integrity.pin()
        self.write_reproduce()
        if self.state.get('active') is None:
            # An empty workbench has no preview owner. Captures, scientific
            # settings and undo stay on disk; only reproducible caches expire.
            self._render_cache.clear();self._panel_cache.clear();self._view_family=None
        return self.state

    def validate_state(self,state,group_ids=None,figure_ids=None):
        for item in state['figures']+state.get('groups',[]):
            if 'libraryDeleted' in item and not isinstance(item['libraryDeleted'],bool):raise ValueError('图件删除标记必须为布尔值')
        figures={f['id']:f for f in state['figures']}
        for record in state['figures']:
            if figure_ids is not None and record['id'] not in figure_ids:continue
            if record['backend']!='matplotlib' and any(p.get('enabled') or p.get('correlation','none')!='none' for p in record.get('native',{}).get('fits',{}).values()):raise ValueError('拟合与相关分析需要原生 XY 数据；请先接入原语言代码与数据')
            if record['backend']!='svg' and record.get('native',{}).get('vectorBindings'):raise ValueError('显式 SVG 绑定只用于 SVG 来源')
            for patch in record.get('overrides',{}).values():
                if 'd' in patch.get('attrs',{}):
                    from vector_tools import path_valid
                    path_valid(patch['attrs']['d'])
                if 'gradientStops' in patch:adjustments.validate_svg_gradient(patch['gradientStops'])
            adjustments.validate(record['style'],record.get('native',{}),record.get('axes',[]))
            semantics.validate(record.get('native',{}))
            from vector_tools import validate_record
            validate_record(self,record)
            if record.get('native',{}).get('categoryLayouts'):self.render_figure(record)
        for group in state.get('groups',[]):
            if group_ids is not None and group.get('id') not in group_ids:continue
            if 'canvasLayoutLocked' in group and not isinstance(group['canvasLayoutLocked'],bool):raise ValueError('画布布局锁定状态必须为布尔值')
            adjustments.finite(group.get('width',12),.2,60);adjustments.finite(group.get('height',8),.2,60)
            for key in ('gap','gapX','gapY'):
                if key in group.get('layout',{}):adjustments.finite(group['layout'][key],0,.5)
            if 'plotFrameSize' in group:
                if not isinstance(group['plotFrameSize'],list) or len(group['plotFrameSize'])!=2:raise ValueError('坐标框尺寸必须为宽高两个值')
                for value in group['plotFrameSize']:adjustments.finite(value,.0001,60)
            for panel in group.get('panels',[]):
                if panel.get('syncLocked') is not None and not isinstance(panel['syncLocked'],bool):raise ValueError('子图联动锁必须为布尔值')
                if panel.get('labelStyle'):
                    adjustments.validate(deep_merge(DEFAULT_STYLE,panel['labelStyle']),{},[])
                    adjustments.finite(panel['labelStyle'].get('alpha',1),0,1)
                    adjustments.finite(panel['labelStyle'].get('rotation',0),-360,360)
                    for key in ('letterSpacing','wordSpacing'):adjustments.finite(panel['labelStyle'].get(key,0),-20,100)
                    if panel['labelStyle'].get('textAnchor','start') not in ('start','middle','end'):raise ValueError('未知文字对齐方式')
                if panel.get('layoutMode','follow') not in ('follow','independent','locked'):raise ValueError('未知子图布局模式')
                for key in ('x','y','w','h'):adjustments.finite(panel[key],.0001 if key in ('w','h') else 0,1)
                merged=resolve_panel(figures[panel['figure']],panel.get('settings',{}),_readonly=True)
                if merged['backend']!='matplotlib' and any(p.get('enabled') or p.get('correlation','none')!='none' for p in merged.get('native',{}).get('fits',{}).values()):raise ValueError('拟合与相关分析需要原生 XY 数据；请先接入原语言代码与数据')
                for patch in merged.get('overrides',{}).values():
                    if 'd' in patch.get('attrs',{}):
                        from vector_tools import path_valid
                        path_valid(patch['attrs']['d'])
                    if 'gradientStops' in patch:adjustments.validate_svg_gradient(patch['gradientStops'])
                adjustments.validate(merged['style'],merged.get('native',{}),merged.get('axes',[]))
                semantics.validate(merged.get('native',{}))
                from vector_tools import validate_record
                validate_record(self,merged)
                if merged.get('native',{}).get('categoryLayouts'):self.render_figure(merged)

    def find(self, fid):
        for f in self.state['figures']+self.state['groups']:
            if f['id']==fid: return f
        raise ValueError('图件不存在')

    def inspect(self,fid,panel=0,full=False,_verified=False,composition=None):
        if not _verified:self.integrity.verify()
        self.view_focus(fid,composition)
        record=self.find(fid)
        if 'panels' in record:
            group=record
            selected=record['panels'][int(panel)]
            record=self.panel_record(group,selected,int(panel))
        # Metadata reads must not inflate and discard the cached SVG.
        # The whole source set was verified above (or by the batched caller).
        key=self._render_key(record,144)
        if key not in self._render_cache:self.render_figure(record)
        self._render_cache.move_to_end(key)
        cached=self._render_cache[key]
        if full and ('fullInspection' in cached or '_fullInspection_gzip' in cached):return self.cache_inspection(cached,True)
        inspection=self.cache_inspection(cached)
        semantic=inspection.get('semantic',{})
        if full and record['backend']=='matplotlib' and semantic.get('entityCount',0)>len(semantic.get('entities',[])):
            # Load full relationships on demand for marquee selection. Ordinary
            # figure opening keeps its bounded, inexpensive inspector payload.
            fig=self.native_figure(record)
            try:inspection['semantic']=fig._fam_graph.describe(limit=len(fig._fam_graph.entities))
            finally:plt.close(fig)
            cached['fullInspection']=copy.deepcopy(inspection)
            self.cache_put(self._render_cache,self._render_key(record,144),cached,32,64*1024*1024)
        return inspection

    @verified
    def inspect_panels(self,fid,composition=None):
        # One source-set check for one batched read. Each render/cache lookup
        # still verifies the particular capture it uses.
        self.integrity.verify()
        self.view_focus(fid,composition)
        item=self.find(fid)
        return {str(i):self.inspect(fid,i,_verified=True,composition=composition) for i in range(len(item.get('panels',[None])))}

    @verified
    def view(self,fid,panel=0,inspection_only=False,composition=None,mode='full'):
        self.view_focus(fid,composition)
        if mode=='panel' and 'panels' in self.find(fid):
            # The panel-only phase reads exactly the entered panel. The inspection
            # is derived from the same resolved panel_record, so axis handles and
            # semantic geometry match the SVG without resolving the whole group.
            inspection=self.inspect(fid,panel,composition=composition)
            return {'inspection':inspection} if inspection_only else {'svg':self.render_panel(fid,panel),'inspection':inspection}
        result={'inspection':self.inspect(fid,panel,composition=composition)} if inspection_only else {'svg':self.render(fid),'inspection':self.inspect(fid,panel,composition=composition)}
        return result

    @staticmethod
    def cache_put(cache,key,value,limit,byte_limit):
        # Bound both entry count and retained payload, allowing one oversized
        # figure to remain usable. Caches are in memory, never extra disk files.
        # Retain lossless compressed large SVG and metadata payloads; decode
        # only the requested result. Python object sizes include dict/list
        # overhead, rather than assuming JSON bytes equal resident memory.
        for name in ('svg','body','inspection','fullInspection'):
            payload=value.get(name)
            if payload is None:continue
            from json_protocol import json_safe
            raw=(payload if isinstance(payload,str) else json.dumps(json_safe(payload),ensure_ascii=False,separators=(',',':'),allow_nan=False)).encode('utf-8')
            if len(raw)<8192:continue
            packed=gzip.compress(raw,compresslevel=1,mtime=0)
            if len(packed)<len(raw)*.8:
                value['_'+name+'_gzip']=packed;del value[name]
        seen=set()
        def size_of(item):
            if id(item) in seen:return 0
            seen.add(id(item));size=sys.getsizeof(item)
            if isinstance(item,dict):size+=sum(size_of(k)+size_of(v) for k,v in item.items() if k!='_bytes')
            elif isinstance(item,(list,tuple)):size+=sum(map(size_of,item))
            return size
        value['_bytes']=size_of(value)
        cache[key]=value;cache.move_to_end(key)
        size=sum(v['_bytes'] for v in cache.values())
        while len(cache)>1 and (len(cache)>limit or size>byte_limit):
            _,removed=cache.popitem(last=False);size-=removed['_bytes']

    @staticmethod
    def cache_text(value,name):
        packed=value.get('_'+name+'_gzip')
        return gzip.decompress(packed).decode('utf-8') if packed is not None else value[name]

    @staticmethod
    def cache_inspection(value,full=False):
        name='fullInspection' if full else 'inspection'
        packed=value.get('_'+name+'_gzip')
        return json.loads(gzip.decompress(packed)) if packed is not None else copy.deepcopy(value[name])

    def view_focus(self,fid,composition=None):
        """Interactive view focus: retain render bodies for one composition family.

        Exactly one composition context is retained. An explicit composition
        (sent by the browser) wins when it really contains the figure; otherwise
        the currently open family is preserved when its member is opened; else
        the first live parent is chosen deterministically. Deleted groups and
        unrelated groups that share the figure are never unioned into the family.
        Export, preview, source verification, shared panels and undo records are
        unaffected; only cached preview bodies outside the focused family are
        released, so a later open re-renders them from immutable captures.
        """
        try:item=self.find(fid)
        except Exception:return
        groups=[g for g in self.state.get('groups',[]) if not g.get('libraryDeleted')]
        group=None
        if 'panels' in item:
            group=item
        else:
            if composition:
                candidate=next((g for g in groups if g.get('id')==composition),None)
                if candidate is not None and any(p.get('figure')==fid for p in candidate.get('panels',[])):
                    group=candidate
            if group is None and self._view_family and fid in self._view_family:
                group=next((g for g in groups if g.get('id') != fid and g.get('id') in self._view_family
                            and any(p.get('figure')==fid for p in g.get('panels',[]))),None)
            if group is None:
                group=next((g for g in groups if any(p.get('figure')==fid for p in g.get('panels',[]))),None)
        family={fid}
        if group is not None:
            family.add(group['id'])
            family.update(p['figure'] for p in group.get('panels',[]) if p.get('figure'))
        if family==self._view_family:return
        self._view_family=family
        for cache in (self._render_cache,self._panel_cache):
            for key in list(cache):
                owner=cache[key].get('_owner')
                if owner is not None and owner not in family:cache.pop(key,None)

    def cache_stats(self):
        def summary(cache):return {'entries':len(cache),'bytes':sum(item.get('_bytes',0) for item in cache.values()),'owners':sorted({str(item.get('_owner')) for item in cache.values() if item.get('_owner') is not None})}
        return {'render':summary(self._render_cache),'panel':summary(self._panel_cache),'focus':len(self._view_family or ())}

    def original_settings(self,fid,panel=0):
        record=self.find(fid)
        if 'panels' in record:record=self.find(record['panels'][int(panel)]['figure'])
        style=deep_merge(DEFAULT_STYLE,record.get('baseline',{}))
        if record['backend']=='svg':
            root=clean_svg((self.root/record['svg']).read_text(encoding='utf-8'))
            vb=list(map(float,root.get('viewBox').split()));style.update(width=vb[2]/72,height=vb[3]/72)
        style.update(preserveOriginal=True,edited=[])
        return {'style':style,'native':{},'overrides':{},'affine':{},'originalBaseline':True}

    def original_preview(self,fid,panel=0):
        """Compare capture with edits without replacing state or saving a revision."""
        self.integrity.verify(force=True)
        item=self.find(fid);panel=int(panel)
        if 'panels' in item:
            if not 0<=panel<len(item['panels']):raise ValueError('子图不存在')
            source=copy.deepcopy(self.find(item['panels'][panel]['figure']))
            current=self.panel_record(item,item['panels'][panel],panel)
        else:
            if panel!=0:raise ValueError('单图没有此子图')
            source=copy.deepcopy(item);current=copy.deepcopy(item)
        original=copy.deepcopy(source);original.update(self.original_settings(fid,panel))
        return {'beforeSVG':self.render_figure(original),'afterSVG':self.render_figure(current),
                'name':source['name'],'panel':panel if 'panels' in item else None,
                'baseline':'current-source-capture','beforeSize':[original['style']['width']*25.4,original['style']['height']*25.4],
                'afterSize':[current['style']['width']*25.4,current['style']['height']*25.4]}


    def _render_key(self,record,dpi):
        values={k:record.get(k) for k in ('id','backend','cache','svg','style','native','overrides','affine','template','chartType')}
        path=self.root/(record.get('cache') or record.get('svg'))
        return hashlib.sha256(json.dumps([values,dpi,path.stat().st_mtime_ns],sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    @verified
    def preview_object(self,fid,panel,item,scene_axis=None):
        """Render a validated presentation draft without saving or replacing sources."""
        self.integrity.verify()
        previous=self.state;original=self.find(fid);panel=int(panel)
        if not isinstance(item,dict) or item.get('id')!=fid:raise ValueError('预览对象身份不匹配')
        fields={'style','native','overrides','affine','originalBaseline'}
        if 'panels' in original:
            fields={'panels'}
            if not 0<=panel<len(original['panels']) or len(item.get('panels',[]))!=len(original['panels']):raise ValueError('预览子图不存在')
            allowed={'settings','label','labelStyle','labelX','labelY','autoLabel','autoTitle','layoutMode'}
            for before,after in zip(original['panels'],item['panels']):
                if {k:v for k,v in before.items() if k not in allowed}!={k:v for k,v in after.items() if k not in allowed}:raise ValueError('预览不能更换来源或子图布局')
        elif panel!=0:raise ValueError('单图没有此子图')
        if {k:v for k,v in original.items() if k not in fields}!={k:v for k,v in item.items() if k not in fields}:raise ValueError('预览仅允许修改展示设置')
        candidate=copy.deepcopy(item)
        try:
            self.state={**previous,**{key:[candidate if r['id']==fid else r for r in previous.get(key,[])] for key in ('figures','groups')}}
            # Synchronization edits group containers, so isolate those first.
            self.state['groups']=copy.deepcopy(self.state.get('groups',[]))
            from group_frames import synchronize
            synchronize(self.state,previous)
            self.validate_state(self.state);semantics.guard_state(previous,self.state)
            if scene_axis is not None:
                active=self.find(fid)
                record=self.panel_record(active,active['panels'][panel],panel) if 'panels' in active else active
                if record['backend']!='matplotlib':raise ValueError('交互三维需要原生 XYZ 或明确的立体几何')
                from spatial_scene import scene
                fig=self.native_figure(record)
                try:return {'scene':scene(fig,int(scene_axis),record.get('native',{}))}
                finally:plt.close(fig)
            return {'svg':self.render(fid)}
        finally:self.state=previous

    @verified
    def preview(self,fid,panel,patch):
        previous=self.state
        try:
            self.state={**previous,'figures':[copy.deepcopy(f) if f['id']==fid else f for f in previous['figures']],'groups':copy.deepcopy(previous.get('groups',[]))};item=self.find(fid)
            if 'panels' in item:
                selected=item['panels'][int(panel)];settings=selected.setdefault('settings',{})
                settings['native']=deep_merge(resolve_panel(self.find(selected['figure']),settings).get('native',{}),patch)
                if 'position' in patch.get('figureTitle',{}):selected['autoTitle']=False
            else:item['native']=deep_merge(item.get('native',{}),patch)
            from group_frames import synchronize
            synchronize(self.state,previous)
            self.validate_state(self.state);semantics.guard_state(previous,self.state)
            return {'svg':self.render(fid),'inspection':self.inspect(fid,panel)}
        finally:self.state=previous

    def add_figure(self,fig,name,source=None,provenance=None):
        fid='f-'+uuid.uuid4().hex[:10]; assign_ids(fig)
        cache=f'figures/{fid}.figure'; (self.root/cache).write_bytes(serialize_figure(fig))
        axes,baseline=adjustments.describe(fig)
        record={'id':fid,'name':name,'backend':'matplotlib','cache':cache,'source':source,
                'style':deep_merge(DEFAULT_STYLE,baseline),'baseline':baseline,'metadataVersion':2,
                'overrides':{},'native':{},'axes':axes,'provenance':provenance or {'kind':'source'}}
        from editability import figure_report
        record['editability']=figure_report(fig)
        declared=getattr(fig,'_fam_chart_type',None)
        if declared is not None:
            if declared not in {kind for kind,_,_ in templates.CATALOG}:raise ValueError('未支持的显式图型：'+str(declared))
            record['chartType']=declared
        self.registry[fid]=copy.deepcopy(record)
        from planar_workflow import declared
        for ai,ax in enumerate(fig.axes):
            if declared(ax):record.setdefault('native',{}).setdefault('spatial',{})[str(ai)]={'phase':'plane','plane':0,'confirmed':False}
        self.state['figures'].append(record); self.state['active']=fid
        (self.root/f'figures/{fid}.svg').write_text(self.render_figure(record),encoding='utf-8')
        plt.close(fig); return record

    def template(self,kind,title=None):
        from distributions import capture
        curated=kind in {k for k,_,_ in templates.CATALOG}
        with capture(): figure=templates.build(kind,title=title,edition='single-v3' if curated else None)
        source={'kind':'synthetic-demo','seed':20261007,'template':kind}
        if curated:
            from scientific_templates import provenance
            source={**provenance(kind),'templateEdition':'single-v3','designEdition':'publication-20261011'}
        elif kind in templates.PAPER_DETAILS:
            from paper_templates import provenance
            source=provenance(kind)
        elif kind in templates.BASIC_DETAILS:
            from basic_paper_templates import provenance
            source=provenance(kind)
        record=self.add_figure(figure,title or dict((k,n) for k,n,_ in templates.CATALOG).get(kind,kind),provenance=source)
        record['template']=kind; self.materialize_source(record); self.save(); return record

    def materialize_source(self,record):
        """Keep a readable drawing script alongside the captured figure/data."""
        provenance=record.get('provenance',{});kind=provenance.get('template')
        if provenance.get('kind') not in ('synthetic-demo','dataset','published-summary') or not kind:return
        script=f'''# Figure as My Mind: {provenance['kind']}. Source inputs and analysis are explicit.
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
import bootstrap
from templates import build
'''
        if provenance['kind']=='dataset':
            dataset=next(d for d in self.state['datasets'] if d['id']==provenance['dataset'])
            script+=f'rows = json.loads((ROOT / {dataset["file"]!r}).read_text(encoding="utf-8"))\n'
            if provenance.get('excludedRows'):
                script+=f'excluded = set({provenance["excludedRows"]!r})\nrows = [row for i, row in enumerate(rows) if i not in excluded]\n'
            script+=f'fig = build({kind!r}, rows, {provenance["mapping"]!r}, title={record["name"]!r})\n'
        else:
            mode='Published aggregate data' if provenance['kind']=='published-summary' else f"Synthetic seed: {provenance.get('seed',20261007)}"
            legacy = kind in templates.BASIC_DETAILS and provenance.get('seed')==20261007 and not provenance.get('templateEdition')
            edition=", edition="+repr(provenance['templateEdition']) if provenance.get('templateEdition') in ('single-v2','single-v3') else ", edition='legacy'" if legacy else ''
            script+=f'fig = build({kind!r}, title={record["name"]!r}'+edition+f')  # {mode}\n'
        if kind in templates.PAPER_DETAILS or provenance.get('templateEdition') in ('paper-v1','single-v2','single-v3'):
            fig=self.native_figure(record,draw=False)
            try:atomic_json(self.root/f'sources/{record["id"]}.template-data.json',fig._fam_template_data)
            finally:plt.close(fig)
            module='scientific_templates.py' if provenance.get('templateEdition') in ('single-v2','single-v3') else 'basic_paper_templates.py' if kind in templates.BASIC_DETAILS else 'paper_templates.py'
            from analysis_templates import BUILDERS as ANALYSIS_BUILDERS
            if kind in ANALYSIS_BUILDERS:module='analysis_templates.py'
            from map_templates import KINDS as MAP_KINDS
            if kind in MAP_KINDS:module='map_templates.py'
            script+=f'# Input/demo records: sources/{record["id"]}.template-data.json\n# Drawing implementation: runtime/{module}\n'
            reference=provenance.get('paperReference',{}).get('url') or provenance.get('referenceURL')
            if reference: script+=f'# Reference: {reference}\n'
            script+=f'# {provenance["dataStatement"]}\n'
        script+=f'fig.savefig(ROOT / "exports" / {safe_name(record["name"])+"_source.svg"!r}, format="svg")\n'
        source=f'sources/{record["id"]}.py';(self.root/source).write_text(script,encoding='utf-8');record['source']=source

    def import_python(self,path,argv=None,require_3d=False):
        path=Path(path).resolve()
        if path.suffix.lower()!='.py': raise ValueError('源文件必须是 .py')
        data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
        old_argv=sys.argv[:]; old_cwd=Path.cwd(); sys.argv=[str(path)]+(argv or [])
        captured=[]; seen=set(); snapshots=set(); orig_save=Figure.savefig; orig_close=plt.close; orig_show=plt.show
        def capture(fig,snapshot=False):
            if not fig.axes:return
            if not snapshot and id(fig) in seen:return
            data=serialize_figure(fig);key=(id(fig),hashlib.sha256(data).hexdigest())
            if key not in snapshots:
                captured.append(pickle.loads(data));snapshots.add(key)
            seen.add(id(fig))
        def savefig(fig,*args,**kwargs):
            capture(fig,snapshot=True)
            # Capture is read-only with respect to source output files.
        def close(fig=None):
            if fig=='all':
                for number in plt.get_fignums(): capture(plt.figure(number))
            elif isinstance(fig,Figure): capture(fig)
            elif fig is None and plt.get_fignums(): capture(plt.gcf())
            elif isinstance(fig,(int,str)) and fig in plt.get_fignums(): capture(plt.figure(fig))
            orig_close(fig)
        Figure.savefig=savefig; plt.close=close; plt.show=lambda *a,**kw: None
        try:
            from distributions import capture as capture_distributions
            os.chdir(path.parent); sys.path.insert(0,str(path.parent))
            with capture_distributions(): namespace=runpy.run_path(str(path),run_name='__main__')
            for number in plt.get_fignums(): capture(plt.figure(number))
        finally:
            Figure.savefig=orig_save; plt.close=orig_close; plt.show=orig_show
            os.chdir(old_cwd); sys.argv=old_argv
            if str(path.parent) in sys.path: sys.path.remove(str(path.parent))
            orig_close('all')
        if not captured: raise ValueError('未发现 Matplotlib 图对象；Plotly、R 或其他语言请导出 SVG 再导入')
        if require_3d:
            from editability import figure_report,require_3d as check_3d
            from planar3d import promote_insets
            for fig in captured:
                promote_insets(fig);check_3d(figure_report(fig))
        declared_files=list(namespace.get('FAM_INPUT_FILES',[]))
        for fig in captured:declared_files.extend(getattr(fig,'_fam_input_files',[]))
        files={};dependencies={}
        for relative in dict.fromkeys(declared_files):
            if not isinstance(relative,str):raise ValueError('源码依赖路径必须为字符串')
            name=Path(relative);original=(path.parent/name).resolve()
            if name.is_absolute() or not original.is_relative_to(path.parent):raise ValueError('源码依赖仅支持绘图脚本目录内的相对路径：'+relative)
            if not original.is_file():raise ValueError('找不到声明的源码依赖：'+relative)
            if original==path:continue
            files[name.as_posix()]={'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'bytes':original.stat().st_size}
            dependencies[name]=original
        bundle_hash=hashlib.sha256(json.dumps([digest,files],sort_keys=True).encode()).hexdigest()[:12]
        bundle=self.root/'sources'/f'{path.stem}-{bundle_hash}'
        bundle.mkdir(parents=True,exist_ok=True);snapshot=bundle/path.name;snapshot.write_bytes(data)
        for name,original in dependencies.items():
            target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,target)
        records=[]
        for i,fig in enumerate(captured):
            name=fig.axes[0].get_title() or (fig._suptitle.get_text() if fig._suptitle is not None else '') or f'{path.stem} · {i+1}'
            records.append(self.add_figure(fig,name,str(snapshot.relative_to(self.root)),
                                         {'kind':'original-source','originalPath':str(path),'sha256':digest,'figureIndex':i,'inputFiles':files,
                                          'dataStatement':getattr(fig,'_fam_data_statement','')}))
        self.extract_namespace(namespace,str(snapshot.relative_to(self.root)),digest)
        self.save(); return records

    def extract_namespace(self,namespace,source,digest):
        """Expose source-script data as selectable candidates; never choose a model."""
        seen_frames=set();arrays={}
        for name,value in namespace.items():
            if name.startswith('_'):continue
            if type(value).__name__=='DataFrame' and type(value).__module__.startswith('pandas.'):
                if id(value) in seen_frames or not 1<=len(value)<=100000 or len(value.columns)>100:continue
                seen_frames.add(id(value))
                if value.columns.has_duplicates:continue
                dataset=self.add_dataset(value.to_csv(index=False),f'{name} · 脚本数据表.csv')
                dataset['provenance']={'kind':'script-dataframe','variable':name,'source':source,'sourceSha256':digest}
            elif isinstance(value,(np.ndarray,list,tuple)) and not isinstance(value,np.ma.MaskedArray):
                try:a=np.asarray(value)
                except (ValueError,TypeError):continue
                if a.ndim==1 and 2<=len(a)<=100000 and a.dtype.kind in 'biufSU':
                    arrays.setdefault(len(a),[]).append((name,a))
        for length,columns in arrays.items():
            columns=columns[:100];text=io.StringIO();writer=csv.writer(text)
            writer.writerow(['row_index']+[name for name,_ in columns])
            for i in range(length):writer.writerow([i+1]+[a[i] for _,a in columns])
            dataset=self.add_dataset(text.getvalue(),f'脚本变量 · {length} 行.csv')
            dataset['provenance']={'kind':'script-arrays','variables':[name for name,_ in columns],'source':source,'sourceSha256':digest,'rowIndex':'generated sequential row number'}

    def import_svg(self,text,name,source=None):
        fid='f-'+uuid.uuid4().hex[:10]; root=clean_svg(text); svg=f'figures/{fid}.base.svg'
        (self.root/svg).write_text(svg_string(root),encoding='utf-8')
        vb=[float(x) for x in root.get('viewBox').split()]
        record={'id':fid,'name':name,'backend':'svg','svg':svg,'source':source,'style':deep_merge(DEFAULT_STYLE,{'width':vb[2]/72,'height':vb[3]/72}),
                'overrides':{},'native':{},'axes':[],'provenance':{'kind':'vector-import','semanticText':sum(n.tag.split('}')[-1]=='text' for n in root.iter())}}
        self.state['figures'].append(record); self.state['active']=fid; self.save(); return record

    def import_image(self,data,name):
        image=Image.open(io.BytesIO(data)); image.load(); output=io.BytesIO(); image.convert('RGBA').save(output,format='PNG')
        w,h=image.size
        text=f'<svg xmlns="{NS}" xmlns:xlink="{XLINK}" viewBox="0 0 {w} {h}"><image id="raster-reference" width="{w}" height="{h}" xlink:href="data:image/png;base64,{base64.b64encode(output.getvalue()).decode()}"/></svg>'
        record=self.import_svg(text,name); record['provenance']={'kind':'raster-reference','reconstructionRequired':True,'pixelSize':[w,h]}
        self.save(); return record

    def add_dataset(self,text,name):
        delimiter='\t' if name.lower().endswith('.tsv') else ','
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),delimiter=delimiter); rows=list(reader)
        if not rows or not reader.fieldnames: raise ValueError('数据文件需要表头和至少一行数据')
        if len(set(reader.fieldnames))!=len(reader.fieldnames) or any(not c.strip() for c in reader.fieldnames):raise ValueError('数据列名不能为空或重复')
        if any(None in row for row in rows):raise ValueError('数据行列数多于表头，请检查分隔符')
        if len(rows)>100000: raise ValueError('交互导入最多 100000 行；更大数据请由脚本筛选后接入')
        columns=dataset_columns(rows,reader.fieldnames)
        did='d-'+uuid.uuid4().hex[:10]; file=f'sources/{did}.json'; atomic_json(self.root/file,rows)
        record={'id':did,'name':name,'rows':len(rows),'columns':columns,'columnsVersion':2,'file':file,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        self.state['datasets'].append(record); self.save(); return record

    def batch(self,payload):
        dataset=next((d for d in self.state['datasets'] if d['id']==payload['dataset']),None)
        if not dataset: raise ValueError('请先选择数据集')
        columns={c['name']:c for c in dataset['columns']}; targets=payload.get('targets',[])
        if not targets or len(targets)>100: raise ValueError('请选择 1–100 个目标变量')
        for t in targets:
            if t not in columns or not columns[t]['numeric']: raise ValueError(f'{t} 不满足数值列要求')
        rows=json.loads((self.root/dataset['file']).read_text(encoding='utf-8'))
        from distributions import capture
        def build(*args,**kwargs):
            with capture(): return templates.build(*args,**kwargs)
        generated=[];specifications=[]
        # Build everything before mutating project: invalid mappings cannot leave a partial batch.
        mapping=payload.get('mapping',{}); kind=payload.get('kind','scatter');policy=payload.get('missingPolicy','error')
        if kind in ('pca','heatmap') and payload.get('mode')=='matrix':
            current=dict(mapping,features=targets);selected,excluded=batch_filter(rows,current,kind,policy);specifications.append((kind.upper(),current,selected,excluded))
            targets=[]
        for target in targets:
            current=dict(mapping,y=target);selected,excluded=batch_filter(rows,current,kind,policy);specifications.append((target,current,selected,excluded))
        previous_figures=set(plt.get_fignums())
        try:
            for target,current,selected,excluded in specifications:generated.append((target,current,build(kind,selected,current,title=target),excluded))
        except Exception:
            for number in set(plt.get_fignums())-previous_figures:plt.close(number)
            raise
        records=[]
        for target,current,fig,excluded in generated:
            record=self.add_figure(fig,target,provenance={'kind':'dataset','dataset':dataset['id'],'mapping':current,'template':kind,'sha256':dataset['sha256'],'missingPolicy':policy,'sourceRows':len(rows),'rowsUsed':len(rows)-len(excluded),'excludedRows':excluded})
            record['style']=deep_merge(record['style'],payload.get('style',{})); self.materialize_source(record); records.append(record)
        self.save(); return records

    def native_figure(self,record,*,draw=True):
        # Only self-created project cache files are loaded. Never accept uploaded pickles.
        self.integrity.verify(record['cache'])
        fig=pickle.loads((self.root/record['cache']).read_bytes()); s=deep_merge(DEFAULT_STYLE,record['style']); n=record.get('native',{})
        if record.get('provenance',{}).get('kind') in ('synthetic-demo','published-summary') and n.get('hideTemplateFooter',True):
            from scientific_templates import remove_footer
            remove_footer(fig)
        if n.get('newick') and record.get('template')=='tree':
            plt.close(fig);fig=templates.build('tree',mapping={'newick':n['newick']},title=record['name']);assign_ids(fig)
        fig._fam_graphkind=record.get('template') or record.get('chartType') or n.get('semanticKind') or getattr(fig,'_fam_chart_type',None)
        fig._fam_fit_template=record.get('template') if record.get('provenance',{}).get('templateEdition') in ('paper-v1','single-v2','single-v3') else None
        self.recover_distributions(fig,record)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
        import geometry
        fig._fam_baseline_axes=[geometry.describe_axis(ax) for ax in fig.axes]
        from planar_workflow import prepare,finish
        n=prepare(fig,n)
        fig=adjustments.apply(fig,s,n,draw=False)
        finish(fig,n)
        if n.get('compositionHeader'):
            from composition import apply_header
            apply_header(fig,n['compositionHeader'])
        from spatial import identify_guides
        identify_guides(fig)
        from planar3d import sort_planes,clip_maps,align_map_axes
        align_map_axes(fig,n)
        clip_maps(fig,n)
        sort_planes(fig)
        if draw:fig.canvas.draw()
        return fig

    def recover_distributions(self,fig,record):
        """Old known templates can read their actual inputs without replacing caches."""
        provenance=record.get('provenance',{});kind=provenance.get('template')
        if kind not in ('box','violin') or any(hasattr(ax,'_fam_boxes') or hasattr(ax,'_fam_violins') for ax in fig.axes):return
        from distributions import capture,recover
        fresh=None
        if provenance.get('kind')=='synthetic-demo' and provenance.get('seed')==20261007:
            with capture():fresh=templates.build(kind,title=record['name'],edition='legacy')
        elif provenance.get('kind')=='dataset':
            dataset=next((d for d in self.state['datasets'] if d['id']==provenance.get('dataset')),None)
            if dataset and dataset.get('sha256')==provenance.get('sha256'):
                rows=json.loads((self.root/dataset['file']).read_text(encoding='utf-8'))
                excluded=set(provenance.get('excludedRows',[]));rows=[row for i,row in enumerate(rows) if i not in excluded]
                with capture():fresh=templates.build(kind,rows,provenance['mapping'],title=record['name'])
        if fresh is not None:
            try:assign_ids(fresh);recover(fig,fresh)
            finally:plt.close(fresh)

    def render_figure(self,record,raster_dpi=144):
        self.integrity.verify(record.get("cache") or record.get("svg"))
        key=self._render_key(record,raster_dpi)
        if key in self._render_cache:
            self._render_cache.move_to_end(key);return self.cache_text(self._render_cache[key],'svg')
        if record['backend']=='matplotlib':
            # savefig performs the actual layout/draw. Avoid a duplicate Agg pass.
            fig=self.native_figure(record,draw=False); output=io.StringIO()
            try:
                with matplotlib.rc_context({'svg.fonttype':'none','svg.hashsalt':record['id']}): fig.savefig(output,format='svg',dpi=raster_dpi,metadata={'Date':None})
                root=semantics.mark_svg(clean_svg(output.getvalue()),fig._fam_graph)
                entity_styles=fig._fam_graph.svg_styles()
                # Derived solid faces already contain the applied source color
                # plus side shading. A flat SVG fill would erase that shading.
                for eid,patch in entity_styles.get('entities',{}).items():
                    entity=fig._fam_graph.entities[eid]
                    if entity.get('displayXYZ') is not None and entity['kind']!='point':patch.pop('style',None)
                # SVG draw caches automatic label positions in 72-dpi display
                # coordinates; describe them in the same units before restoring.
                fig.set_dpi(72)
                axes,style=adjustments.describe(fig)
                for ai,a in enumerate(axes):
                    legend=fig.axes[ai].get_legend()
                    if legend:
                        # Legend.draw stores frame bounds in the SVG renderer's
                        # 72-dpi display coordinates even when frameon=False.
                        x,y,w,h=legend.get_frame().get_bbox().bounds
                        a['legend']['layoutBox']=[float(x),float(fig.get_figheight()*72-y-h),float(w),float(h)]
                limit=len(fig._fam_graph.entities) if any(p.get('followEntity') for p in record.get('overrides',{}).values()) else 2000
                inspection={'spatial':__import__('spatial').describe(fig,record.get('native',{})),'axes':axes,'baselineAxes':fig._fam_baseline_axes,'figureTitle':__import__('geometry').describe_title(fig._suptitle),'style':style,'semantic':fig._fam_graph.describe(limit=limit)}
            finally:plt.close(fig)
        else:
            root=clean_svg((self.root/record['svg']).read_text(encoding='utf-8'))
            if record.get('native',{}).get('vectorBindings'):
                from vector_tools import apply_bindings
                apply_bindings(self,root,record['native'])
            inspection={'axes':record.get('axes',[]),'semantic':semantics.generic_info(root)}
            if record.get('chartType') in ('bar','box','violin','histogram','forest'):
                for entity in inspection['semantic']['entities']:entity['movementLocked']=True
                if inspection['semantic']['entities']:inspection['semantic']['warnings'].append('此统计矢量图未提供分类轴和同类别系列布局；保留数值位置，间距调整需通过原语言适配。')
        if record['backend']=='matplotlib':
            from legend_layout import apply_svg
            apply_svg(root,fig,record.get('native',{}),inspection)
        if record['backend']=='svg' and not record['style'].get('transparent') and ('background' in record['style'].get('edited',[]) or not record['style'].get('preserveOriginal',True)):
            vb=[float(v) for v in root.get('viewBox').split()]
            root.insert(0,ET.Element(f'{{{NS}}}rect',{'id':'fam-background','x':str(vb[0]),'y':str(vb[1]),'width':str(vb[2]),'height':str(vb[3]),'fill':record['style'].get('background','#fff')}))
        from workflow_graphics import svg_math,svg_comparisons
        svg_math(root,record.get('native',{}))
        root=patch_svg(root,dict(record.get('style',{}),_backend=record['backend']),record.get('overrides',{}))
        if record['backend']=='svg':
            root=semantics.generic_apply(root,record.get('native',{}))
            from workflow_graphics import svg_group_mappings
            svg_group_mappings(root,record.get('native',{}))
            svg_comparisons(root,record.get('native',{}))
        # New text annotations explicitly follow an observation, independently
        # of their own user-controlled offsets and typography.
        bound={gid:p for gid,p in record.get('overrides',{}).items() if p.get('followEntity')}
        if bound:
            entities={e['id']:e for e in inspection.get('semantic',{}).get('entities',[])}
            nodes={n.get('id'):n for n in root.iter() if n.get('id')};parents={c:p for p in root.iter() for c in p}
            for gid,props in bound.items():
                entity=entities.get(props['followEntity']);node=nodes.get(gid)
                if entity is None or node is None:raise ValueError('绑定注释的观测不存在或超出当前语义读取范围')
                position=entity.get('display')
                if position is None:
                    owner=nodes[entity['artist']]
                    anchor=owner.get('data-fam-anchor')
                    if anchor:
                        xy=json.loads(anchor)
                        if len(xy)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in xy):raise ValueError('SVG 注释锚点须为两个有限数值')
                    elif owner.tag.split('}')[-1]=='circle':xy=[float(owner.get('cx')),float(owner.get('cy'))]
                    elif owner.tag.split('}')[-1]=='rect':xy=[float(owner.get('x',0))+float(owner.get('width',0))/2,float(owner.get('y',0))]
                    else:raise ValueError('此 SVG 对象需要声明 data-fam-anchor 注释锚点')
                    position=np.array([*xy,1.])
                    while owner is not None:
                        position=semantics.svg_transform_matrix(owner.get('transform',''))@position;owner=parents.get(owner)
                    position=position[:2]
                offset=props.get('labelOffset',[6,-6]);node.set('x',str(position[0]+offset[0]));node.set('y',str(position[1]+offset[1]));node.set('data-fam-bound',entity['id'])
                native=record.get('native',{})
                if native.get('entities',{}).get(entity['id'],{}).get('hidden') or not native.get('layers',{}).get('data',{}).get('visible',True):
                    set_css(node,{'display':'none'})
        from workflow_graphics import svg_math,svg_comparisons
        semantics.style_entities_svg(root,entity_styles if record['backend']=='matplotlib' else record.get('native',{}))
        for node in root.iter():
            if node.get('id','').startswith('annotation-'):
                node.set('data-fam-layer','annotation')
                config=record.get('native',{}).get('layers',{}).get('annotation',{})
                if not config.get('visible',True):set_css(node,{'display':'none'})
                values={k:str(v) for k,v in config.get('style',{}).items()}
                css={a:values[k] for k,a in [('fontSize','font-size'),('fontFamily','font-family'),('fontWeight','font-weight'),('fontStyle','font-style'),('color','fill'),('lineWidth','stroke-width'),('alpha','opacity')] if k in values}
                # Independent object styles take precedence over annotation-layer defaults.
                set_css(node,{**css,**record.get('overrides',{}).get(node.get('id'),{}).get('css',{})})
        from workflow_graphics import svg_leaders
        svg_leaders(root,record.get('overrides',{}))
        # Explicit physical dimensions are consistent across preview and export.
        s=record['style']; root.set('width',f'{s.get("width",6.4)*72}pt'); root.set('height',f'{s.get("height",4.8)*72}pt')
        root.set('data-fid',record['id'])
        if record.get('affine'):
            a=record['affine']; contents=[n for n in list(root) if n.tag.split('}')[-1] not in ('defs','metadata')]
            g=ET.SubElement(root,f'{{{NS}}}g',{'transform':f'matrix({a.get("a",1)} {a.get("b",0)} {a.get("c",0)} {a.get("d",1)} {a.get("tx",0)} {a.get("ty",0)})'})
            for node in contents: root.remove(node); g.append(node)
        if record['backend']=='matplotlib':
            from spatial import transform_svg,tag_svg
            tag_svg(root,fig)
            transform_svg(root,fig,record.get('native',{}),inspection)
        value=svg_string(root)
        self.cache_put(self._render_cache,key,{'svg':value,'inspection':inspection,'_owner':record['id']},32,64*1024*1024)
        return value

    def panel_svg(self,figure,index,raster_dpi,attributes,_verified=False):
        # A prepared panel still belongs to an immutable capture. Check it even
        # on cache hits; mtime alone cannot detect replacement/tampering.
        if not _verified:self.integrity.verify(figure.get('cache') or figure.get('svg'))
        # Prefix IDs/clip paths once per rendered child, not on each layout move.
        key=(self._render_key(figure,raster_dpi),index)
        prepared=self._panel_cache.get(key)
        if prepared is None:
            child=ET.fromstring(self.render_figure(figure,raster_dpi));prefix=f'p{index}-'
            original_ids={n.get('id') for n in child.iter() if n.get('id')}
            for node in child.iter():
                if node.get('id'):node.set('data-original-id',node.get('id'));node.set('id',prefix+node.get('id'))
                for name,value in list(node.attrib.items()):
                    if 'url(#' in value:node.set(name,value.replace('url(#','url(#'+prefix))
                    if name.endswith('href') and value.startswith('#'):node.set(name,'#'+prefix+value[1:])
                if node.tag.split('}')[-1]=='style' and node.text:
                    node.text=re.sub(r'#([\w-]+)(?=[\s,.>{:\[]|$)',lambda m:'#'+prefix+m[1] if m[1] in original_ids else m[0],node.text)
            serialized=svg_string(child)
            opening=serialized[:serialized.index('>')]
            namespaces=dict(re.findall(r'(xmlns(?::[\w-]+)?)="([^"]*)"',opening))
            namespaces.pop('xmlns',None)
            prepared={'attrs':{**child.attrib,**namespaces},'body':serialized[serialized.index('>')+1:],'_owner':figure['id']}
            self.cache_put(self._panel_cache,key,prepared,32,32*1024*1024)
        else:self._panel_cache.move_to_end(key)
        shell=ET.Element(f'{{{NS}}}svg',{**prepared['attrs'],**attributes})
        return svg_string(shell).removesuffix(' />')+'>'+self.cache_text(prepared,'body')

    def panel_record(self,group,panel,index):
        figure=resolve_panel(self.find(panel['figure']),panel.get('settings',{}),_readonly=True)
        if group.get('physicalFonts') and figure['backend']=='matplotlib':
            figure['style']['width']=panel['w']*group['width'];figure['style']['height']=panel['h']*group['height']
        if group.get('transparent',True):figure['style']['transparent']=True
        if group.get('autoPanelTitles',True) and panel.get('autoTitle',True) and figure['backend']=='matplotlib' and not figure.get('native',{}).get('layers',{}).get('annotation',{}).get('locked'):
            from composition import title_settings
            figure=title_settings(figure,group,panel,index,_readonly=True)
        return figure

    def render_panel(self,fid,panel=0,raster_dpi=144,transparent=None):
        """Render only the resolved current panel of one composition.

        This is a real panel-only path: it uses the same panel_record as the full
        composition render, never builds the group shell, never touches sibling
        panels, and caches under a phase/panel-specific key.
        """
        record=self.find(fid)
        if 'panels' not in record:raise ValueError('当前图不是组图，不能使用逐张编辑的子图视图')
        panel=int(panel)
        if not 0<=panel<len(record['panels']):raise ValueError('子图不存在')
        entry=record['panels'][panel]
        source=self.find(entry['figure'])
        self.integrity.verify(source.get('cache') or source.get('svg'))
        figure=self.panel_record(record,entry,panel)
        if transparent is not None:figure['style']['transparent']=transparent
        from sequential_compositions import panel_view_signature
        key='panelview:'+panel_view_signature(self,record,entry,panel,raster_dpi)
        if key in self._render_cache:
            self._render_cache.move_to_end(key);return self.cache_text(self._render_cache[key],'svg')
        width=float(entry['w'])*float(record.get('width',12))*72
        height=float(entry['h'])*float(record.get('height',8))*72
        value=self.panel_svg(figure,panel,raster_dpi,{'x':'0','y':'0','width':str(width),'height':str(height),'data-panel':str(panel),'overflow':'visible'},_verified=True)
        self.cache_put(self._render_cache,key,{'svg':value,'_owner':fid},32,64*1024*1024)
        return value

    def render(self,fid,raster_dpi=144,transparent=None):
        record=copy.deepcopy(self.find(fid))
        if transparent is not None:
            if 'panels' in record:record['transparent']=transparent
            else:record['style']['transparent']=transparent
        if 'panels' not in record: return self.render_figure(record,raster_dpi)
        # Verify unique captures together: shared parent identities and manifest
        # parsing are reused, including when every child uses prepared SVG.
        self.integrity.verify([self.find(p['figure']).get('cache') or self.find(p['figure']).get('svg') for p in record['panels']])
        # Retain complete compositions in the existing bounded compressed LRU.
        # Rechecking captures above remains mandatory even for a cache hit.
        sources={p['figure']:self.find(p['figure']) for p in record['panels']}
        signature=[record,[(fid,f.get('name'),self._render_key(f,raster_dpi)) for fid,f in sorted(sources.items())]]
        key='composition:'+hashlib.sha256(json.dumps(signature,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
        if key in self._render_cache:
            self._render_cache.move_to_end(key);return self.cache_text(self._render_cache[key],'svg')
        w=float(record.get('width',12))*72; h=float(record.get('height',8))*72
        root=ET.Element(f'{{{NS}}}svg',{'width':f'{w}pt','height':f'{h}pt','viewBox':f'0 0 {w} {h}'})
        if not record.get('transparent',True):ET.SubElement(root,f'{{{NS}}}rect',{'width':str(w),'height':str(h),'fill':record.get('background','#fff')})
        shell=svg_string(root)
        opening=shell[:-6] if shell.endswith('</svg>') else shell.removesuffix(' />')+'>'
        parts=[opening]
        for i,panel in enumerate(record['panels']):
            figure=self.panel_record(record,panel,i)
            parts.append(self.panel_svg(figure,i,raster_dpi,{'x':str(panel['x']*w),'y':str(panel['y']*h),'width':str(panel['w']*w),'height':str(panel['h']*h),'data-panel':str(i),'overflow':'visible'},_verified=True))
            if record.get('labels',True):
                auto=record.get('autoPanelTitles',True) and panel.get('autoLabel',True)
                label=ET.SubElement(root,f'{{{NS}}}text',{'id':f'fam-panel-{i}-label','data-panel-label':str(i),'x':str(panel['x']*w+(6 if auto else panel.get('labelX',3))),'y':str(panel['y']*h+(6+record.get('labelSize',16)*.9 if auto else panel.get('labelY',17))),
                         'font-size':str(panel.get('labelStyle',{}).get('fontSize',record.get('labelSize',16))),'font-family':panel.get('labelStyle',{}).get('fontFamily',record.get('labelFamily','Arial')),
                         'font-weight':panel.get('labelStyle',{}).get('fontWeight',record.get('labelWeight','bold')),'font-style':panel.get('labelStyle',{}).get('fontStyle','normal'),'fill':panel.get('labelStyle',{}).get('textColor',record.get('labelColor','#243742')),'opacity':str(panel.get('labelStyle',{}).get('alpha',1)),'text-anchor':panel.get('labelStyle',{}).get('textAnchor','start'),'dominant-baseline':panel.get('labelStyle',{}).get('dominantBaseline','auto'),'letter-spacing':str(panel.get('labelStyle',{}).get('letterSpacing',0)),'word-spacing':str(panel.get('labelStyle',{}).get('wordSpacing',0)),'pointer-events':'all'})
                if panel.get('labelStyle',{}).get('rotation'):label.set('transform',f"rotate({panel['labelStyle']['rotation']} {label.get('x')} {label.get('y')})")
                label.text=panel.get('label',chr(97+i))
                parts.append(svg_string(label));root.remove(label)
        value=''.join(parts)+'</svg>'
        if record.get('workflow',{}).get('shared'):
            from workflow_graphics import common_guides
            value=common_guides(self,record,value)
        self.cache_put(self._render_cache,key,{'svg':value,'_owner':fid},32,64*1024*1024)
        return value

    def export(self,fid,fmt='svg',dpi=600,path=None,transparent=None,_defer=False):
        if fmt not in ('svg','png','pdf','tiff'): raise ValueError('支持 SVG / PNG / PDF / TIFF')
        if not 72<=int(dpi)<=1200: raise ValueError('DPI 范围 72–1200')
        self.integrity.verify(force=True)
        record=self.find(fid);name=safe_name(record['name'])
        if sum(safe_name(f['name'])==name for f in self.state['figures']+self.state['groups'])>1:name+='_'+fid
        destination=Path(path) if path else self.root/'exports'/f'{name}.{fmt}'
        width=record.get('width',record.get('style',{}).get('width',6.4));height=record.get('height',record.get('style',{}).get('height',4.8))
        if width*height*int(dpi)**2>100_000_000:raise ValueError('输出超过一亿像素，请降低尺寸或 DPI')
        destination.parent.mkdir(parents=True,exist_ok=True); svg=self.render(fid,raster_dpi=int(dpi),transparent=transparent)
        if _defer:return svg,destination
        if fmt=='svg': destination.write_text(svg,encoding='utf-8'); return destination
        return export_svg(svg,destination,fmt,int(dpi))

    @staticmethod
    def write_if_changed(path,text):
        if not path.exists() or path.read_text(encoding='utf-8')!=text:path.write_text(text,encoding='utf-8')

    def write_reproduce(self):
        text='''# Generated by Figure as My Mind. Applies saved settings to the captured data and figures.
from pathlib import Path
import argparse, sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runtime"))
from engine import Project
p = argparse.ArgumentParser()
p.add_argument("--format", choices=["svg", "png", "pdf", "tiff"], default="svg")
p.add_argument("--dpi", type=int, default=600)
p.add_argument("--ids", nargs="*")
p.add_argument("--transparent", action="store_true", default=None)
p.add_argument("--output", type=Path, help="Export directory; defaults to the project's exports folder")
a = p.parse_args()
project = Project(ROOT)
for item in project.state["figures"] + project.state["groups"]:
    if not a.ids and item.get("libraryDeleted"): continue
    if not a.ids or item["id"] in a.ids:
        destination = a.output / (item["id"] + "." + a.format) if a.output else None
        print(project.export(item["id"], a.format, a.dpi, path=destination, transparent=a.transparent))
'''
        self.write_if_changed(self.root/'reproduce.py',text)
        native='''# Apply native formats, axes, legends, series, colorbars and camera settings.
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runtime"))
import bootstrap
from adjustments import apply
from distributions import capture as capture_plot_inputs
STYLE = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
def apply_fam_style(fig, figure_id=None):
    from engine import assign_ids
    items = STYLE["figures"]
    selected = next((f for f in items if f["id"] == figure_id), items[0])
    assign_ids(fig)
    fig._fam_graphkind = selected.get("template") or selected.get("chartType") or selected.get("native", {}).get("semanticKind") or getattr(fig, "_fam_chart_type", None)
    return apply(fig, selected["style"], selected.get("native", {}))
# SVG object transforms and composition require reproduce.py for exact replay.
# For box/violin statistical variants, build the figure inside `with capture_plot_inputs():`.
'''
        self.write_if_changed(self.root/'apply_style.py',native)


def browser_executable():
    configured=os.environ.get('FAM_BROWSER')
    if configured: return configured
    for path in [Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe',
                 Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe']:
        if path.exists(): return str(path)
    return None


def export_svg(svg,destination,fmt,dpi):
    try: from playwright.sync_api import sync_playwright
    except ImportError: raise RuntimeError('PNG/PDF/TIFF 导出需要 playwright；运行 setup.py 安装。SVG 导出无需浏览器依赖。')
    root=ET.fromstring(svg)
    def points(value): return float(re.match(r'[\d.]+',value)[0])
    w=points(root.get('width')); h=points(root.get('height')); pixelw=round(w*dpi/72); pixelh=round(h*dpi/72)
    if pixelw*pixelh>100_000_000: raise ValueError('输出超过一亿像素，请降低尺寸或 DPI')
    root.set('width','100%'); root.set('height','100%')
    with sync_playwright() as p:
        executable=browser_executable(); kwargs={'executable_path':executable} if executable else {}
        browser=p.chromium.launch(headless=True,**kwargs)
        page=browser.new_page(viewport={'width':math.ceil(w*96/72),'height':math.ceil(h*96/72)},device_scale_factor=dpi/96)
        page.route('**/*',lambda route: route.abort())
        page.set_content(f'<html><head><style>@page{{size:{w}pt {h}pt;margin:0}} html,body{{margin:0;width:{w}pt;height:{h}pt;overflow:hidden}} svg{{display:block}}</style></head><body>{svg_string(root)}</body></html>')
        page.evaluate('document.fonts.ready'); page.emulate_media(media='screen')
        if fmt=='pdf':
            data=page.pdf(width=f'{w/72}in',height=f'{h/72}in',print_background=True,margin={'top':'0','right':'0','bottom':'0','left':'0'},prefer_css_page_size=True)
            try:import pymupdf
            except ImportError:destination.write_bytes(data)
            else:
                # Chromium quantizes paper dimensions. Normalize the physical
                # page to the requested points while retaining vector contents.
                with pymupdf.open(stream=data,filetype='pdf') as source,pymupdf.open() as exact:
                    sheet=exact.new_page(width=w,height=h);sheet.show_pdf_page(sheet.rect,source,0,keep_proportion=False);exact.save(destination)
        else:
            data=page.screenshot(type='png',omit_background=True)
            image=Image.open(io.BytesIO(data)); image=image.resize((pixelw,pixelh),Image.Resampling.LANCZOS) if image.size!=(pixelw,pixelh) else image
            image.save(destination,format='TIFF' if fmt=='tiff' else 'PNG',dpi=(dpi,dpi),**({'compression':'tiff_lzw'} if fmt=='tiff' else {}))
        browser.close()
    return destination
