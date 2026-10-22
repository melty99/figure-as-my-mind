"""Cheap structural editability checks before delivering a source figure."""

def figure_report(fig):
    axes=[];warnings=[];unsupported=[]
    from planar3d import ImagePlane3D
    from mpl_toolkits.mplot3d.art3d import Path3DCollection,Poly3DCollection,Line3DCollection,Line3D,Patch3D,Text3D
    for i,ax in enumerate(fig.axes):
        colorbar=hasattr(ax,'_colorbar');native3d=hasattr(ax,'zaxis')
        nested=sum(hasattr(c,'_colorbar') for c in ax.child_axes)
        if native3d:
            for artist in [*ax.images,*ax.collections,*ax.lines,*ax.patches,*ax.texts]:
                if artist.get_visible() and not isinstance(artist,(ImagePlane3D,Path3DCollection,Poly3DCollection,Line3DCollection,Line3D,Patch3D,Text3D)):
                    unsupported.append(type(artist).__name__)
        axes.append({'axis':i,'native3D':native3d,'colorbar':colorbar,
                     'axisRanges':True,'insetColorbarsMissing':nested,
                     'schematicDepth':bool(getattr(ax,'_fam_schematic_depth',False))})
        if nested:warnings.append('嵌套色标尚未登记，不能提供完整缩放控制。')
    statement=getattr(fig,'_fam_data_statement','').lower()
    projected=not any(a['native3D'] for a in axes) and ('affine' in statement or 'not a native xyz' in statement)
    if projected:warnings.append('这是平面投影示意图；需要声明图层坐标并适配，才能编辑三维视角。')
    return {'version':1,'axes':axes,'frameResize':bool(axes),'axisRanges':bool(axes),'camera3D':any(a['native3D'] for a in axes),
            'colorbarResize':not any(a['insetColorbarsMissing'] for a in axes),
            'directManipulation3D':not unsupported,'unsupportedGeometry':sorted(set(unsupported)),'projectedOnly':projected,'warnings':list(dict.fromkeys(warnings))}


def require_3d(report):
    if not report.get('camera3D') or not report.get('colorbarResize') or not report.get('directManipulation3D',True):
        raise ValueError('打开前适配未完成：需要原生 XYZ / 明确的三维图层与已登记色标。平面 SVG 或仿射投影不能代替三维相机。')


def record_report(record):
    # Legacy projects can be inspected without unpickling any figure or running
    # source code; a missing report never implies unsupported geometry is ready.
    return record.get('editability') or {'version':1,
        'camera3D':any(a.get('is3d') for a in record.get('axes',[])),
        'colorbarResize':bool(record.get('axes')) and record.get('backend')=='matplotlib',
        'axes':[{'axis':i,'native3D':bool(a.get('is3d')),'colorbar':bool(a.get('isColorbar')),'axisRanges':record.get('backend')=='matplotlib'} for i,a in enumerate(record.get('axes',[]))],
        'warnings':['旧接入需要核对色标、坐标与相机；缺少语义时先适配源代码。']}


def check_project(root):
    import json
    from pathlib import Path
    state=json.loads((Path(root)/'project.fam.json').read_text(encoding='utf-8'))
    figures={r['id']:r for r in state['figures']}
    active=next((r for r in [*state['figures'],*state.get('groups',[])] if r['id']==state.get('active')),None)
    if active is None:raise ValueError('当前没有图件；请先接入已适配的源代码。')
    items=[figures[p['figure']] for p in active['panels']] if 'panels' in active else [active]
    for item in items:require_3d(record_report(item))


def require_axes(report):
    if not report.get('axes') or not all(a.get('axisRanges') for a in report['axes'] if not a.get('colorbar')):
        raise ValueError('坐标编辑尚未适配：普通 SVG 只有图形对象。请从原 R/Python/MATLAB/C 源码登记真实坐标；ggplot 用 fam_save_ggplot，其他已支持几何用 fam-native 场景重新接入。')
