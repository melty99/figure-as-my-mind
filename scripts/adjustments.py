"""Semantic Matplotlib adjustments shared by the studio and saved scripts."""
import math
import numpy as np
from matplotlib import colors, ticker
from matplotlib.text import Text
from matplotlib.markers import MarkerStyle
from mpl_toolkits.mplot3d.art3d import Path3DCollection

class PerPointGlyph3D(Path3DCollection):
    """Sort point-specific paths with the depth-sorted offsets during drawing."""
    def draw(self,renderer):
        original=self._paths;order=getattr(self,'_z_markers_idx',None)
        try:
            if len(original)>1 and isinstance(order,np.ndarray):self._paths=[original[int(i)%len(original)] for i in order]
            return super().draw(renderer)
        finally:self._paths=original

PALETTES = {
    'okabe-ito': ['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00','#56B4E9','#F0E442','#000000'],
    'muted': ['#216e83','#db8851','#6a8e6f','#8876a9','#ce6473','#253d43'],
}


def hex_color(value):
    try: return 'none' if colors.to_rgba(value)[3]==0 else colors.to_hex(value)
    except (ValueError, TypeError): return '#243742'

def validate_gradient(stops, *, svg=False):
    """Native scalar maps are strict; SVG additionally permits padded/hard stops."""
    maximum=256 if svg else 32
    if not isinstance(stops,list) or not 2<=len(stops)<=maximum:raise ValueError('渐变需要 2–'+str(maximum)+' 个颜色节点')
    previous=-1
    for stop in stops:
        if not isinstance(stop,dict):raise ValueError('渐变节点无效')
        position=stop.get('position');finite(position,0,1)
        if position<previous or not svg and position==previous:raise ValueError('SVG 渐变节点位置不能递减' if svg else '渐变节点位置必须严格递增')
        previous=position
        colors.to_rgba(stop.get('color'))
        finite(stop.get('alpha',1),0,1)
    if not svg and (stops[0]['position']!=0 or stops[-1]['position']!=1):raise ValueError('渐变首尾节点的位置必须为 0 和 1')


def validate_svg_gradient(stops):
    """Keep legal SVG endpoint padding and coincident color discontinuities."""
    return validate_gradient(stops,svg=True)


def validate_color_bins(bins):
    if not isinstance(bins,list) or not 1<=len(bins)<=256:raise ValueError('分级色标需要 1–256 个颜色')
    for value in bins:
        if not isinstance(value,dict):raise ValueError('分级颜色无效')
        colors.to_rgba(value.get('color'));finite(value.get('alpha',1),0,1)


def mappable_id(image):
    return getattr(image,'_fam_mapping_id',None) or ((image.get_gid() or 'fam-map-values') if hasattr(image,'get_gid') else 'fam-map-values')


def describe_mapping(image,fig):
    lo,hi=image.get_clim();norm=image.norm;cmap=image.get_cmap();cb=getattr(image,'colorbar',None)
    bins=[]
    if isinstance(norm,colors.BoundaryNorm):
        edges=norm.boundaries;values=[];labels=[]
        if norm.extend in ('min','both'):values.append(float(edges[0])-max(1,abs(float(edges[0]))));labels.append('< '+format(float(edges[0]),'.6g'))
        for low,high in zip(edges[:-1],edges[1:]):values.append(float(low)+(float(high)-float(low))/2);labels.append(format(float(low),'.6g')+' – '+format(float(high),'.6g'))
        if norm.extend in ('max','both'):values.append(float(edges[-1])+max(1,abs(float(edges[-1]))));labels.append('> '+format(float(edges[-1]),'.6g'))
        bins=[{'label':label,'color':colors.to_hex(cmap(norm(v))),'alpha':float(cmap(norm(v))[3])} for v,label in zip(values,labels)]
    return {'id':mappable_id(image),
            'cmap':getattr(cmap,'_fam_preset',cmap.name),'cmapReverse':getattr(cmap,'_fam_reverse',False),
            'cmapStops':getattr(cmap,'_fam_stops',None),'discrete':isinstance(norm,colors.BoundaryNorm),'colorBins':bins,
            'cmapSamples':[{'position':float(v),'color':colors.to_hex(cmap(v)), 'alpha':float(cmap(v)[3])} for v in np.linspace(0,1,9)],
            'clim':[float(lo),float(hi)],'norm':'log' if isinstance(norm,colors.LogNorm) else 'centered' if isinstance(norm,colors.TwoSlopeNorm) else 'linear',
            'center':float(getattr(norm,'vcenter',0)),
            'colorbarAxis':fig.axes.index(cb.ax) if cb and cb.ax in fig.axes else None,
            'colorbarAxes':[i for i,ax in enumerate(fig.axes) if getattr(getattr(ax,'_colorbar',None),'mappable',None) is image],
            'colorbarLabel':cb.ax.get_xlabel() if cb and cb.orientation=='horizontal' else cb.ax.get_ylabel() if cb else ''}


def marker_name(path):
    for name in ('o','s','^','v','<','>','D','d','p','h','H','8','P','X','x','+','*','.','_', '|'):
        m=MarkerStyle(name);p=m.get_path().transformed(m.get_transform())
        if path.vertices.shape==p.vertices.shape and np.allclose(path.vertices,p.vertices) and np.array_equal(path.codes,p.codes):return name
    return '__custom__'


class NaturalLogFormatter(ticker.LogFormatterMathtext):
    """Show natural-log decades as e powers without transforming observations."""
    def __call__(self,value,pos=None):
        return super().__call__(value,pos).replace(str(math.e),'e')


def describe(fig):
    import geometry
    axes=[]
    for ax in fig.axes:
        a={k:getattr(ax,'get_'+k)() for k in ('title','xlabel','ylabel','xscale','yscale')}
        a.update(xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),position=list(ax.get_position().bounds),
                 is3d=hasattr(ax,'zaxis'),isPolar=ax.name=='polar',isColorbar=hasattr(ax,'_colorbar'),visible=ax.get_visible(),axisOn=ax.axison,aspect=ax.get_aspect(),series=[],mappables=[],spines={k:s.get_visible() for k,s in ax.spines.items()})
        a.update(geometry.describe_axis(ax));a['isExtra']=getattr(ax,'_fam_extra',False)
        if a['is3d']:
            a['schematicDepth']=getattr(ax,'_fam_schematic_depth',False)
            a.update(zlabel=ax.get_zlabel(),zlim=list(ax.get_zlim()),
                     camera={'azimuth':ax.azim,'elevation':ax.elev,'roll':ax.roll,'vertical':ax._vertical_axis,
                             'projection':'ortho' if math.isinf(ax._focal_length) else 'persp',
                             'aspect':list(ax.get_box_aspect())})
        for kind,artists in [('line',ax.lines),('patch',ax.patches),('collection',ax.collections),('image',ax.images)]:
            if a['isColorbar']: continue
            for i,artist in enumerate(artists):
                if getattr(artist,'_fam_workflow_inactive',False):continue
                if not artist.get_gid():continue
                label=artist.get_label()
                item={'id':artist.get_gid(),'kind':kind,'name':label if label and not label.startswith('_') else f'{kind} {i+1}'}
                if kind=='line':
                    item.update(color=hex_color(artist.get_color()),lineWidth=artist.get_linewidth(),
                                lineStyle=artist.get_linestyle(),marker=str(artist.get_marker()),markerSize=artist.get_markersize())
                elif kind=='patch': item.update(color=hex_color(artist.get_facecolor()),lineWidth=artist.get_linewidth())
                elif kind=='collection':
                    item['sizeScale']=1
                    item['mappable']=artist.get_array() is not None
                    if hasattr(artist,'get_facecolor'):
                        c=artist.get_facecolor()
                        if len(c):item['color']=hex_color(c[0])
                    if hasattr(artist,'get_paths') and hasattr(artist,'get_sizes'):
                        names={marker_name(p) for p in artist.get_paths()};item['marker']=next(iter(names)) if len(names)==1 else '__mixed__'
                    if hasattr(artist,'get_facecolors'):
                        c=artist.get_facecolors();item['mixedColor']=len(c)>1 and not np.allclose(c,c[0])
                else: item['mappable']=True
                item['alpha']=artist.get_alpha() if artist.get_alpha() is not None else 1
                item['points']=kind=='line' or (hasattr(artist,'get_sizes') and type(artist).__name__ in ('PathCollection','Path3DCollection'))
                item['zorder']=artist.get_zorder();a['series'].append(item)
                if hasattr(artist,'get_array') and artist.get_array() is not None and np.ndim(artist.get_array())<=2:
                    a['mappables'].append(describe_mapping(artist,fig))
        for image in getattr(ax,'_fam_mappables',[]):
            a['mappables'].append(describe_mapping(image,fig))
        legend=ax.get_legend()
        if legend:
            texts=legend.get_texts();frame=legend.get_frame()
            a['legend']={'visible':legend.get_visible(),'loc':str(legend._loc),'ncols':legend._ncols,
                         'fontSize':texts[0].get_fontsize() if texts else 11,'baseFontSize':legend._fontsize,'title':legend.get_title().get_text(),
                         'titleSize':legend.get_title().get_fontsize(),'frame':legend.get_frame_on(),
                         'alpha':frame.get_alpha() if frame.get_alpha() is not None else 1,
                         'faceColor':hex_color(frame.get_facecolor()),'edgeColor':hex_color(frame.get_edgecolor()),
                         'markerScale':legend.markerscale,'labelSpacing':legend.labelspacing,'borderAxesPad':legend.borderaxespad,
                         'columnSpacing':legend.columnspacing,'handleLength':legend.handlelength}
            a['legend']['textColor']=hex_color(texts[0].get_color()) if texts else '#243742'
            a['legend']['titleColor']=hex_color(legend.get_title().get_color())
            a['legend']['entries']=[{'index':j,'label':t.get_text(),'textColor':hex_color(t.get_color()),
                'color':legend_symbol_color(h),'alpha':legend_symbol_alpha(h),'fontSize':t.get_fontsize(),
                'fontFamily':', '.join(t.get_fontfamily()),'fontWeight':t.get_fontweight(),'fontStyle':t.get_fontstyle()} for j,(h,t) in enumerate(zip(legend.legend_handles,texts))]
            graph=getattr(fig,'_fam_graph',None)
            if graph:
                for entry in a['legend']['entries']:
                    sid=graph.legend_series.get((fig.axes.index(ax),entry['index']))
                    if sid:entry['seriesId']=sid
        axes.append(a)
    ax=fig.axes[0] if fig.axes else None
    baseline={'width':float(fig.get_figwidth()),'height':float(fig.get_figheight()),
              'background':hex_color(fig.get_facecolor())}
    if ax:
        ticks=ax.get_xticklabels() or ax.get_yticklabels()
        baseline.update(fontFamily=', '.join(geometry.title_artist(ax)[1].get_fontfamily()),fontSize=ax.xaxis.label.get_fontsize(),
                        titleSize=geometry.title_artist(ax)[1].get_fontsize(),labelSize=ax.xaxis.label.get_fontsize(),
                        tickSize=ticks[0].get_fontsize() if ticks else 10,textColor=hex_color(ax.xaxis.label.get_color()),
                        lineWidth=next(iter(ax.spines.values())).get_linewidth() if ax.spines else 1,spines=any(s.get_visible() for s in ax.spines.values()),
                        grid=any(l.get_visible() for l in ax.get_xgridlines()+ax.get_ygridlines()))
    return axes,baseline


def finite(value, low=None, high=None):
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value):
        raise ValueError('调整参数需要有限数值')
    if low is not None and value<low or high is not None and value>high: raise ValueError('调整参数超出允许范围')


def validate(style,native,axes):
    import geometry
    import fitting
    fitting.validate(native)
    geometry.validate(native,axes)
    for identifier,patch in native.get('mappables',{}).items():
        if not isinstance(identifier,str) or not isinstance(patch,dict):raise ValueError('独立色标参数无效')
        validate({},patch,axes)
    for k in ('width','height'): finite(style.get(k,6.4),.2,60)
    for k in ('fontSize','titleSize','labelSize','tickSize'): finite(style.get(k,11),1,300)
    finite(style.get('lineWidth',1.2),0,50)
    for k in ('background','textColor'):
        if k in style: colors.to_rgba(style[k])
    if native.get('cmap'):
        import matplotlib
        if native['cmap'] not in matplotlib.colormaps: raise ValueError('未知连续色带')
    if native.get('cmapStops') is not None:validate_gradient(native['cmapStops'])
    if native.get('colorBins') is not None:validate_color_bins(native['colorBins'])
    if 'cmapReverse' in native and not isinstance(native['cmapReverse'],bool):raise ValueError('渐变反转参数无效')
    if 'colorNorm' in native and native['colorNorm'] not in ('linear','log','centered'):raise ValueError('未知色标归一化')
    if 'clim' in native:
        limits=native['clim']
        if len(limits)!=2: raise ValueError('色标范围需要两个数值')
        for v in limits: finite(v)
        if limits[0]>=limits[1]: raise ValueError('色标范围必须递增')
        if native.get('colorNorm')=='log' and limits[0]<=0: raise ValueError('对数色标的最小值必须大于 0')
        if native.get('colorNorm')=='centered' and not limits[0]<native.get('colorCenter',0)<limits[1]:
            raise ValueError('色标中心必须位于色标范围内')
    if 'colorCenter' in native: finite(native['colorCenter'])
    for key,patch in native.get('axes',{}).items():
        if not key.isdigit() or int(key)>=len(axes): raise ValueError('坐标区域不存在')
        a=axes[int(key)]
        for dim in ('x','y','z'):
            if dim+'scale' in patch and patch[dim+'scale'] not in ('linear','log','symlog'): raise ValueError('未知坐标尺度')
            if dim+'logBase' in patch:
                base=patch[dim+'logBase'];finite(base)
                if isinstance(base,bool) or base<=0 or base==1:raise ValueError('对数底数必须大于0且不能为1')
            limits=patch.get(dim+'lim',a.get(dim+'lim'))
            if limits is not None:
                if len(limits)!=2: raise ValueError('坐标范围需要两个数值')
                for v in limits: finite(v)
                if limits[0]==limits[1]: raise ValueError('坐标范围的两端不能相同')
                if patch.get(dim+'scale',a.get(dim+'scale'))=='log' and min(limits)<=0: raise ValueError('对数轴的坐标范围必须大于 0')
            if dim+'tickDecimals' in patch: finite(patch[dim+'tickDecimals'],0,10)
            if dim+'tickRotation' in patch: finite(patch[dim+'tickRotation'],-360,360)
            if dim+'labelPad' in patch: finite(patch[dim+'labelPad'],-100,200)
            if dim+'majorTicks' in patch:
                from axis_ticks import validate as validate_major_ticks
                validate_major_ticks(patch[dim+'majorTicks'])
            if dim+'ticks' in patch:
                for v in patch[dim+'ticks']: finite(v)
            if dim+'tickLabels' in patch and len(patch[dim+'tickLabels'])!=len(patch.get(dim+'ticks',[])):
                raise ValueError('自定义刻度文字需与刻度位置数量一致')
        if 'position' in patch:
            if len(patch['position'])!=4: raise ValueError('坐标框位置需要四个数值')
            for v in patch['position']: finite(v,0,1)
            if min(patch['position'][2:])<=0: raise ValueError('坐标框宽高必须大于 0')
        if 'titlePosition' in patch:
            if len(patch['titlePosition'])!=2:raise ValueError('标题位置需要两个数值')
            for v in patch['titlePosition']:finite(v,-5,5)
        for k in ('tickLength','tickWidth','gridWidth','gridAlpha','titlePad'):
            if k in patch: finite(patch[k],0,200)
    for p in [*native.get('artists',{}).values(),*native.get('seriesStyles',{}).values()]:
        for k in ('lineWidth','edgeWidth','markerSize','sizeScale','alpha','zorder'):
            if k in p: finite(p[k],0,1 if k=='alpha' else 300)
        for k in ('color','edgeColor','markerFaceColor','markerEdgeColor'):
            if k in p: colors.to_rgba(p[k])
        if 'marker' in p:MarkerStyle(p['marker'])
        if 'lineStyle' in p:
            from matplotlib.lines import Line2D
            Line2D([],[],linestyle=p['lineStyle'])
    for p in native.get('legends',{}).values():
        if 'scale' in p:finite(p['scale'],.05,20)
        if 'scaleOffset' in p:
            if not isinstance(p['scaleOffset'],list) or len(p['scaleOffset'])!=2:raise ValueError('图例缩放位移需要两个数值')
            for value in p['scaleOffset']:finite(value,-2000,2000)
        if p.get('arrangement','grid') not in ('grid','horizontal','vertical'):raise ValueError('未知图例排列方式')
        if p.get('fillOrder','column') not in ('column','row'):raise ValueError('未知图例填充方向')
        if p.get('symbolSide','original') not in ('original','left','right','top','bottom'):raise ValueError('未知图例符号位置')
        if 'entryOrder' in p:
            order=p['entryOrder']
            if not isinstance(order,list) or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in order) or len(set(order))!=len(order):raise ValueError('图例条目顺序需要不重复的非负整数')
        if 'titleOffset' in p:
            if not isinstance(p['titleOffset'],list) or len(p['titleOffset'])!=2:raise ValueError('图例标题位移需要两个值')
            for v in p['titleOffset']:finite(v,-2000,2000)
        for k in ('faceColor','edgeColor','textColor','titleColor','symbolColor'):
            if k in p:colors.to_rgba(p[k])
        if 'symbolAlpha' in p:finite(p['symbolAlpha'],0,1)
        for key,entry in p.get('entries',{}).items():
            if not key.isdigit():raise ValueError('图例条目索引需要非负整数')
            for k in ('color','edgeColor','textColor'):
                if k in entry:colors.to_rgba(entry[k])
            if 'alpha' in entry:finite(entry['alpha'],0,1)
            if 'styleOrder' in entry:finite(entry['styleOrder'],0)
            for value in entry.get('styleOrders',{}).values():finite(value,0)
            from legend_layout import validate_entry
            validate_entry(entry)
        for k in ('fontSize','titleSize','ncols','markerScale','labelSpacing','columnSpacing','handleLength','handleTextPad','borderAxesPad','alpha'):
            if k in p: finite(p[k],0,1 if k=='alpha' else 100)
        if 'ncols' in p and (p['ncols']<1 or p['ncols']!=int(p['ncols'])): raise ValueError('图例列数需要正整数')
        if 'anchor' in p:
            if len(p['anchor']) not in (2,4): raise ValueError('图例锚点需要两个或四个坐标')
            for v in p['anchor']: finite(v)
    for k,v in native.get('colorbar',{}).items():
        if k=='ticks':
            for number in v: finite(number)
        elif k in ('decimals','labelSize','tickSize','outlineWidth','labelPad'): finite(v,0,200)
    import spatial
    spatial.validate(native)
    for k,v in native.get('camera',{}).items():
        if k=='aspect':
            if len(v)!=3: raise ValueError('XYZ 比例需要三个数值')
            for number in v: finite(number,.001,1000)
        elif k in ('azimuth','elevation','roll'): finite(v,-360,360)


def apply(fig,style,native,*,draw=True):
    from semantics import Graph,validate
    import distributions,variants,geometry
    validate(native);distributions.validate(native);variants.validate(native)
    import fitting
    fitting.prepare(fig)
    distributions.apply(fig,native);variants.apply(fig,native)
    from legend_layout import prepare
    prepare(fig);graph=Graph(fig)
    active=lambda k: (k not in ('fontWeight','fontStyle') or k in style) and (not style.get('preserveOriginal',True) or k in style.get('edited',[]))
    fig.set_size_inches(style.get('width',6.4),style.get('height',4.8))
    if active('background'): fig.set_facecolor(style.get('background','#fff'))
    if style.get('transparent'): fig.patch.set_alpha(0)
    elif getattr(fig,'_fam_design_edition',None):fig.patch.set_alpha(1)
    for text in fig.findobj(match=Text):
        if active('fontFamily'): text.set_fontfamily([f.strip().strip('\'"') for f in style['fontFamily'].split(',')])
        if active('fontSize'): text.set_fontsize(style['fontSize'])
        if active('textColor'): text.set_color(style['textColor'])
        if active('fontWeight'): text.set_fontweight(style.get('fontWeight','normal'))
        if active('fontStyle'): text.set_fontstyle(style.get('fontStyle','normal'))
    colorbars=[]
    for i,ax in enumerate(fig.axes):
        if style.get('transparent'): ax.patch.set_alpha(0)
        elif getattr(fig,'_fam_design_edition',None):ax.patch.set_alpha(1)
        if active('titleSize'):
            for t in (ax.title,ax._left_title,ax._right_title):t.set_fontsize(style['titleSize'])
        for dim in ('x','y','z'):
            axis=getattr(ax,dim+'axis',None)
            if axis and active('labelSize'): axis.label.set_fontsize(style['labelSize'])
        if active('tickSize'): ax.tick_params(labelsize=style['tickSize'])
        if active('grid'): ax.grid(style.get('grid',False),**({'alpha':.25} if style.get('grid') else {}))
        for spine in ax.spines.values():
            if active('lineWidth'): spine.set_linewidth(style['lineWidth'])
            if active('spines'): spine.set_visible(style['spines'])
        if active('lineWidth'):
            for line in ax.lines: line.set_linewidth(style['lineWidth'])
        patch=native.get('axes',{}).get(str(i),{})
        for dim in ('x','y','z'):
            axis=getattr(ax,dim+'axis',None)
            if axis is None: continue
            current_scale=getattr(ax,'get_'+dim+'scale')()
            if dim+'scale' in patch or dim+'logBase' in patch and current_scale=='log':
                scale=patch.get(dim+'scale',current_scale);options={}
                if scale=='log':options['base']=patch.get(dim+'logBase',getattr(axis._scale,'base',10))
                getattr(ax,'set_'+dim+'scale')(scale,**options)
                if scale=='log' and math.isclose(options['base'],math.e,rel_tol=1e-12):axis.set_major_formatter(NaturalLogFormatter(base=math.e))
            if dim+'lim' in patch: getattr(ax,'set_'+dim+'lim')(patch[dim+'lim'])
            if dim+'invert' in patch:
                axis.set_inverted(patch[dim+'invert'])
            if dim+'label' in patch: axis.label.set_text(patch[dim+'label'])
            if dim+'labelPad' in patch: axis.labelpad=patch[dim+'labelPad']
            from axis_ticks import apply as apply_major_ticks
            managed_ticks=apply_major_ticks(ax,dim,patch)
            if dim+'tickLabels' in patch and not managed_ticks: getattr(ax,'set_'+dim+'ticklabels')(patch[dim+'tickLabels'])
            elif dim+'tickFormat' in patch:
                fmt=patch[dim+'tickFormat'];decimals=int(patch.get(dim+'tickDecimals',2))
                if fmt=='fixed': axis.set_major_formatter(ticker.StrMethodFormatter('{x:.'+str(decimals)+'f}'))
                elif fmt=='scientific': axis.set_major_formatter(ticker.StrMethodFormatter('{x:.'+str(decimals)+'e}'))
                elif fmt=='percent': axis.set_major_formatter(ticker.PercentFormatter(patch.get(dim+'percentBase',1),decimals))
            if dim+'tickRotation' in patch: ax.tick_params(axis=dim,which='both',labelrotation=patch[dim+'tickRotation'])
        loc,title=geometry.title_artist(ax,patch.get('titleLoc'));ax._fam_primary_title_loc=loc
        if 'title' in patch:title.set_text(patch['title'])
        if 'titlePad' in patch:ax._set_title_offset_trans(patch['titlePad'])
        if 'titlePosition' in patch:title.set_position(patch['titlePosition']);ax._autotitlepos=False
        for where,tp in patch.get('titles',{}).items():
            t=geometry.title_artist(ax,where)[1]
            if 'text' in tp:t.set_text(tp['text'])
            if 'pad' in tp:
                from matplotlib.transforms import ScaledTranslation
                t.set_transform(ax.transAxes+ScaledTranslation(0,tp['pad']/72,fig.dpi_scale_trans));ax._autotitlepos=False
            if 'position' in tp:t.set_position(tp['position']);ax._autotitlepos=False
        if 'position' in patch:
            if hasattr(ax,'_colorbar'):
                ax.set_axes_locator(None);ax.set_box_aspect(None);ax.set_aspect('auto')
            ax.set_position(patch['position'])
        tickparams={k:patch[v] for k,v in [('length','tickLength'),('width','tickWidth'),('direction','tickDirection')] if v in patch}
        if tickparams: ax.tick_params(**tickparams)
        if 'minorTicks' in patch:
            if patch['minorTicks']: ax.minorticks_on()
            else: ax.minorticks_off()
        if 'grid' in patch:
            ax.grid(patch['grid'],**({k:patch[v] for k,v in [('color','gridColor'),('alpha','gridAlpha'),('linewidth','gridWidth'),('linestyle','gridStyle')] if v in patch} if patch['grid'] else {}))
        for name,visible in patch.get('spines',{}).items():
            if name in ax.spines: ax.spines[name].set_visible(visible)
        if hasattr(ax,'zaxis') and native.get('camera'):
            c=native['camera'];ax.view_init(elev=c.get('elevation',ax.elev),azim=c.get('azimuth',ax.azim),roll=c.get('roll',ax.roll),vertical_axis='xyz'[ax._vertical_axis])
            if 'projection' in c: ax.set_proj_type(c['projection'],**({'focal_length':ax._focal_length if np.isfinite(ax._focal_length) else 1} if c['projection']=='persp' else {}))
            if 'aspect' in c: ax.set_box_aspect(c['aspect'])
        # A categorical collection has no scalar array: do not recolor it as a colorbar.
        mapped=list(ax.images)+list(ax.collections)+getattr(ax,'_fam_mappables',[])
        if hasattr(fig,'_fam_map_mappable') and hasattr(ax,'_colorbar'):mapped=[]
        for image in mapped:
            if image.get_array() is None or np.ndim(image.get_array())>2: continue
            mapping_id=mappable_id(image)
            mapping={**native,**native.get('mappables',{}).get(mapping_id,{})}
            if mapping.get('colorBins') is not None:
                bins=mapping['colorBins'];validate_color_bins(bins);norm=image.norm
                if not isinstance(norm,colors.BoundaryNorm) or len(bins)!=norm._n_regions:raise ValueError('分级颜色数量必须与当前数值区间一致')
                cmap=colors.ListedColormap([colors.to_rgba(v['color'],v.get('alpha',1)) for v in bins],name='fam-bins')
                image.set_cmap(cmap);image.set_norm(colors.BoundaryNorm(norm.boundaries.copy(),len(bins),clip=norm.clip,extend=norm.extend))
            elif mapping.get('cmapStops') is not None:
                from matplotlib.colors import LinearSegmentedColormap
                stops=mapping['cmapStops'];validate_gradient(stops)
                cmap=LinearSegmentedColormap.from_list('fam-custom',[(s['position'],colors.to_rgba(s['color'],s.get('alpha',1))) for s in stops],N=image.norm.Ncmap if isinstance(image.norm,colors.BoundaryNorm) else 256)
                cmap._fam_stops=[dict(s) for s in stops];cmap._fam_preset='fam-custom'
                image.set_cmap(cmap)
            elif mapping.get('cmap') or 'cmapReverse' in mapping:
                import matplotlib
                cmap=matplotlib.colormaps.get_cmap(mapping.get('cmap') or image.get_cmap())
                preset=cmap.name
                if isinstance(image.norm,colors.BoundaryNorm):cmap=cmap.resampled(image.norm.Ncmap)
                if mapping.get('cmapReverse'):cmap=cmap.reversed()
                cmap._fam_preset=preset;cmap._fam_reverse=mapping.get('cmapReverse',False)
                image.set_cmap(cmap)
            limits=mapping.get('clim')
            norm=mapping.get('colorNorm')
            if image is getattr(fig,'_fam_map_mappable',None) and isinstance(image.norm,colors.BoundaryNorm):
                # Classified regions use explicit bin boundaries. Retained
                # continuous-scale settings resume when that mode is restored.
                limits=None;norm=None
            if norm:
                values=np.asarray(image.get_array());lo,hi=limits or [float(np.nanmin(values)),float(np.nanmax(values))]
                if norm=='log':
                    if lo<=0: raise ValueError('对数色标要求正值范围')
                    image.set_norm(colors.LogNorm(lo,hi))
                elif norm=='centered': image.set_norm(colors.TwoSlopeNorm(mapping.get('colorCenter',0),lo,hi))
                else: image.set_norm(colors.Normalize(lo,hi))
            elif limits: image.set_clim(*limits)
            cbar=getattr(image,'colorbar',None)
            if cbar and cbar not in colorbars: colorbars.append(cbar)
        if getattr(ax,'_fam_mappables',[]):
            from map_templates import colorize
            colorize(fig)
            if getattr(fig,'_fam_track_mappable',None) is not None:
                mapper=fig._fam_track_mappable
                for row,bars in zip(mapper.get_array(),fig._fam_track_bars):
                    for value,bar in zip(row,bars):bar.set_facecolor(mapper.cmap(mapper.norm(value)))
        palette=PALETTES.get(native.get('palette'))
        if palette and not hasattr(ax,'_colorbar') and not getattr(fig,'_fam_track_mappable',None):
            for j,line in enumerate(l for l in ax.lines if not l.get_label().startswith('_')): line.set_color(palette[j%len(palette)])
            for j,container in enumerate(ax.containers):
                if type(container).__name__=='BarContainer':
                    for bar in container.patches: bar.set_facecolor(palette[j%len(palette)])
            for j,c in enumerate(c for c in ax.collections if c.get_array() is None):
                parent=getattr(c,'_fam_parent_bar',None)
                if parent is not None:c.set_edgecolor(parent.get_facecolor())
                else:c.set_facecolor(palette[j%len(palette)])
            for line in ax.lines:
                parent=getattr(line,'_fam_series_line',None)
                if parent is not None:line.set_color(parent.get_color());line.set_markeredgecolor(parent.get_color())
            if not any(type(c).__name__=='BarContainer' for c in ax.containers):
                for j,p in enumerate(p for p in ax.patches if type(p).__name__ in ('Wedge','PathPatch')):p.set_facecolor(palette[j%len(palette)])
        for artist in list(ax.lines)+list(ax.patches)+list(ax.collections)+list(ax.images):
            p=native.get('artists',{}).get(artist.get_gid(),{})
            for key,setter in [('alpha','set_alpha'),('zorder','set_zorder'),('lineWidth','set_linewidth'),('lineStyle','set_linestyle'),
                               ('markerSize','set_markersize'),('markerFaceColor','set_markerfacecolor'),('markerEdgeColor','set_markeredgecolor'),('edgeColor','set_edgecolor')]:
                if key in p and hasattr(artist,setter): getattr(artist,setter)(p[key])
            if 'color' in p:
                if artist in ax.lines: artist.set_color(p['color'])
                elif type(artist).__name__=='LineCollection': artist.set_color(p['color'])
                elif hasattr(artist,'set_facecolor'): artist.set_facecolor(p['color'])
            if 'marker' in p:
                if hasattr(artist,'set_marker'): artist.set_marker(p['marker'])
                elif hasattr(artist,'set_paths') and hasattr(artist,'get_sizes'):
                    m=MarkerStyle(p['marker']);artist.set_paths([m.get_path().transformed(m.get_transform())])
            if 'sizeScale' in p and hasattr(artist,'get_sizes'): artist.set_sizes(artist.get_sizes()*p['sizeScale'])
        lp=native.get('legends',{}).get(str(i),{})
        legend=ax.get_legend()
        if legend and lp:update_legend_layout(legend,lp)
    for cbar in colorbars:
        # Figure capture drops weak colorbar callbacks. Explicitly update its
        # declared shared scalar mapping and retain the stable SVG identity.
        mapper=cbar.mappable
        if cbar.norm is not mapper.norm or cbar.cmap is not mapper.cmap or cbar.vmin!=mapper.norm.vmin or cbar.vmax!=mapper.norm.vmax:
            gid=cbar.solids.get_gid() if cbar.solids is not None else None
            cbar.update_normal(mapper)
            if gid and cbar.solids is not None:cbar.solids.set_gid(gid)
        mapping_id=mappable_id(cbar.mappable)
        p={**native.get('colorbar',{}),**native.get('mappables',{}).get(mapping_id,{}).get('colorbar',{})}
        if 'label' in p: cbar.set_label(p['label'],labelpad=p.get('labelPad',4),fontsize=p.get('labelSize',style.get('labelSize',12)))
        if 'ticks' in p: cbar.set_ticks(p['ticks'])
        if 'decimals' in p: cbar.formatter=ticker.StrMethodFormatter('{x:.'+str(int(p['decimals']))+'f}');cbar.update_ticks()
        if 'tickSize' in p: cbar.ax.tick_params(labelsize=p['tickSize'])
        if 'outlineWidth' in p: cbar.outline.set_linewidth(p['outlineWidth'])
        if 'visible' in p: cbar.ax.set_visible(p['visible'])
    fig._fam_graph=graph
    graph.apply(native)
    from workflow_graphics import native_follow
    native_follow(fig,native)
    distributions.update_demo_caption(fig,native)
    import fitting
    fitting.apply(fig,native,graph)
    ft=native.get('figureTitle')
    if ft:
        text=fig._suptitle
        if text is None:text=fig.suptitle(ft.get('text',''));text.set_gid('fam-figure-title');graph.owner(text,'annotation')
        if 'text' in ft:text.set_text(ft['text'])
        geometry.text_style(text,ft)
        if 'position' in ft:text.set_position(ft['position']);text._autopos=False
    apply_legend_styles(fig,native)
    import geometry
    if native.get('secondaryAxes') or any(any(k in p for k in ('labelStyles','tickStyles','spineStyles','titleStyles','titles')) for p in native.get('axes',{}).values()):
        geometry.finish(fig,native,graph)
    for text in fig.findobj(match=Text):geometry.text_fallback(text)
    import spatial
    spatial.apply(fig,native,graph)
    if draw:fig.canvas.draw()
    return fig


def legend_symbol_color(handle):
    empty=False
    for getter in ('get_markerfacecolor','get_facecolor','get_color','get_markeredgecolor','get_edgecolor'):
        if hasattr(handle,getter):
            try:
                value=getattr(handle,getter)()
                if isinstance(value,str) and value=='auto':continue
                if isinstance(value,str) and value.lower()=='none':empty=True;continue
                a=np.asarray(value)
                if not a.size:empty=True;continue
                return hex_color(a[0] if a.ndim==2 else value)
            except (ValueError,TypeError):pass
    return 'none' if empty else '#216e83'


def legend_symbol_alpha(handle):
    """RGBA can encode opacity even when Artist.alpha is unset."""
    value=handle.get_alpha()
    if value is not None:
        a=np.asarray(value);return float(a.flat[0])
    for getter in ('get_markerfacecolor','get_facecolor','get_color','get_edgecolor'):
        if hasattr(handle,getter):
            try:
                c=getattr(handle,getter)();a=np.asarray(c)
                if isinstance(c,str) and c.lower() in ('none','auto') or not a.size:continue
                return float(colors.to_rgba(a[0] if a.ndim==2 and len(a) else c)[3])
            except (ValueError,TypeError,IndexError):pass
    return 1.


def update_legend_layout(legend,p):
    """Repack the captured entries, retaining custom handlers and text styles."""
    from matplotlib.offsetbox import HPacker,VPacker,DrawingArea
    from matplotlib.transforms import Affine2D
    old_font=legend._fontsize;old_length=legend.handlelength;old_scale=legend.markerscale
    if 'fontSize' in p:
        legend._fontsize=p['fontSize'];legend.prop.set_size(p['fontSize'])
        for text in legend.get_texts():text.set_fontsize(p['fontSize'])
    for key,attr in [('ncols','_ncols'),('markerScale','markerscale'),('labelSpacing','labelspacing'),('columnSpacing','columnspacing'),('handleLength','handlelength'),('handleTextPad','handletextpad')]:
        if key in p:setattr(legend,attr,int(p[key]) if key=='ncols' else p[key])
    if 'title' in p:legend.set_title(p['title'])
    if 'titleSize' in p:legend.get_title().set_fontsize(p['titleSize'])
    if 'frame' in p:legend.set_frame_on(p['frame'])
    if 'visible' in p:legend.set_visible(p['visible'])
    if p.get('anchorReset'):legend.set_bbox_to_anchor(None)
    elif 'anchor' in p:legend.set_bbox_to_anchor(p['anchor'])
    if 'borderAxesPad' in p:legend.borderaxespad=p['borderAxesPad']
    if 'loc' in p:
        loc=p['loc'];legend.set_loc(int(loc) if isinstance(loc,str) and loc.isdigit() else loc)
    keys=('ncols','fontSize','markerScale','labelSpacing','columnSpacing','handleLength','handleTextPad','arrangement','fillOrder','entryOrder','symbolSide','entries')
    if not any(k in p for k in keys):return
    from legend_layout import rows as captured_rows,repack
    font=legend._fontsize;rows=captured_rows(legend)
    for row in rows:
        row.sep=legend.handletextpad*font
        for area in row.get_children():
            if not isinstance(area,DrawingArea):continue
            sx=(legend.handlelength*font)/(old_length*old_font) if old_length*old_font else 1;sy=font/old_font
            for artist in area.get_children():
                if sx!=1 or sy!=1:
                    trans=Affine2D().scale(sx,sy)
                    if hasattr(artist,'get_offsets') and hasattr(artist,'set_offset_transform'):artist.set_offset_transform(trans+artist.get_offset_transform())
                    elif hasattr(artist,'get_data_transform'):artist.set_transform(trans+artist.get_data_transform())
                    else:artist.set_transform(trans+artist.get_transform())
                ratio=legend.markerscale/old_scale if old_scale else 1
                if hasattr(artist,'get_markersize'):artist.set_markersize(artist.get_markersize()*ratio)
                elif hasattr(artist,'get_sizes'):artist.set_sizes(artist.get_sizes()*ratio**2)
            area.width*=sx;area.height*=sy;area.ydescent*=sy
    repack(legend,p)


def apply_series_colors(artist,p):
    """Apply explicit edges after face/series color; preserve uncertainty artists."""
    if 'color' in p:
        # Filled glyphs retain explicit outlines; default 'face' edges still follow.
        from matplotlib.lines import Line2D
        from matplotlib.collections import LineCollection
        if hasattr(artist,'set_facecolor') and not isinstance(artist,(Line2D,LineCollection)):artist.set_facecolor(p['color'])
        elif hasattr(artist,'set_color'):artist.set_color(p['color'])
        if 'markerFaceColor' not in p and hasattr(artist,'set_markerfacecolor'):artist.set_markerfacecolor(p['color'])
        if 'markerEdgeColor' not in p and 'edgeColor' not in p and hasattr(artist,'set_markeredgecolor'):artist.set_markeredgecolor(p['color'])
    for key,setter in [('alpha','set_alpha'),('lineWidth','set_linewidth'),('markerFaceColor','set_markerfacecolor'),('markerEdgeColor','set_markeredgecolor')]:
        if key in p and hasattr(artist,setter):getattr(artist,setter)(p[key])
    if 'edgeColor' in p:
        setter=getattr(artist,'set_markeredgecolor',None) or getattr(artist,'set_edgecolor',None)
        if setter:setter(p['edgeColor'])
    if 'edgeWidth' in p:
        setter=getattr(artist,'set_markeredgewidth',None) or getattr(artist,'set_linewidth',None)
        if setter:setter(p['edgeWidth'])


def apply_legend_styles(fig,native):
    from semantics import Graph
    from matplotlib.offsetbox import DrawingArea
    for ai,ax in enumerate(fig.axes):
        legend=ax.get_legend();p=native.get('legends',{}).get(str(ai),{})
        if not legend or not p:continue
        frame=legend.get_frame()
        if 'faceColor' in p:frame.set_facecolor(p['faceColor'])
        if 'edgeColor' in p:frame.set_edgecolor(p['edgeColor'])
        if 'alpha' in p:frame.set_alpha(p['alpha'])
        if 'titleColor' in p:legend.get_title().set_color(p['titleColor'])
        # A legend entry may contain a marker, error stem and caps. All its
        # DrawingArea artists receive the same explicit symbol edit.
        from legend_layout import areas as captured_areas,apply_text,apply_part_style
        areas=captured_areas(legend)
        for j,(area,text) in enumerate(zip(areas,legend.get_texts())):
            entry=p.get('entries',{}).get(str(j),{})
            graph=getattr(fig,'_fam_graph',None);sid=graph.legend_series.get((ai,j)) if graph else None
            series=native.get('seriesStyles',{}).get(sid,{})
            entry=dict(entry)
            for k in ('color','edgeColor','edgeWidth','alpha'):
                if k in series and (k not in entry or series.get('orders',{}).get(k,series.get('order',0))>entry.get('styleOrders',{}).get(k,entry.get('styleOrder',0))):entry[k]=series[k]
            s={k:p[v] for k,v in [('color','symbolColor'),('alpha','symbolAlpha')] if v in p};s.update({k:entry[k] for k in ('color','edgeColor','edgeWidth','alpha') if k in entry})
            for artist in area.findobj():
                apply_series_colors(artist,s)
            if 'textColor' in p:text.set_color(p['textColor'])
            if 'textColor' in entry:text.set_color(entry['textColor'])
            apply_text(text,entry)
            for k,artist in enumerate(area.get_children()):apply_part_style(artist,entry.get('parts',{}).get(str(k),{}))


def describe_legend(legend):
    frame=legend.get_frame();texts=legend.get_texts()
    return {'ncols':legend._ncols,'fontSize':texts[0].get_fontsize() if texts else 11,'frame':legend.get_frame_on(),
            'alpha':frame.get_alpha() if frame.get_alpha() is not None else 1,'faceColor':hex_color(frame.get_facecolor()),
            'edgeColor':hex_color(frame.get_edgecolor()),'title':legend.get_title().get_text(),
            'titleSize':legend.get_title().get_fontsize(),'markerScale':legend.markerscale,
            'labelSpacing':legend.labelspacing,'columnSpacing':legend.columnspacing,'handleLength':legend.handlelength}
