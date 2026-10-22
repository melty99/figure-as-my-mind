"""Retain distribution inputs and artists; never infer samples from quartiles."""
import copy
from contextlib import contextmanager
import numpy as np
from matplotlib.axes import Axes
from matplotlib import cbook
from matplotlib.colors import to_hex, to_rgba


def samples(x):
    return [np.asarray(np.ma.asarray(v, dtype=float).compressed())[np.isfinite(np.ma.asarray(v, dtype=float).compressed())].copy()
            for v in cbook._reshape_2D(x, 'X')]


@contextmanager
def capture():
    """Hook public plotting calls only while executing an authorized drawing script."""
    original_box, original_bxp, original_violin = Axes.boxplot, Axes.bxp, Axes.violinplot
    def bxp(ax, stats, *args, **kwargs):
        # Normalize positional arguments without changing their meaning.
        import inspect
        bound = inspect.signature(original_bxp).bind(ax, stats, *args, **kwargs)
        bound.apply_defaults(); options = bound.arguments
        result = original_bxp(ax, stats, *args, **kwargs)
        horizontal = options.get('orientation') == 'horizontal' or options.get('vert') is False
        records = getattr(ax, '_fam_boxes', [])
        for i, box in enumerate(result['boxes']):
            parts = {'box': [box]}
            for key in ('medians', 'means', 'fliers'):
                if len(result[key]) == len(result['boxes']): parts[{'medians':'median','means':'mean','fliers':'points'}[key]] = [result[key][i]]
            for key in ('whiskers', 'caps'):
                parts[{'whiskers':'whisker','caps':'cap'}[key]] = result[key][2*i:2*i+2]
            records.append({'parts': parts, 'stats': copy.deepcopy(stats[i]), 'samples': None, 'horizontal': horizontal,
                            'notched': bool(options.get('shownotches')), 'patch': bool(options.get('patch_artist')), 'meanline': bool(options.get('meanline'))})
        ax._fam_boxes = records
        return result
    def boxplot(ax, x, *args, **kwargs):
        before = len(getattr(ax, '_fam_boxes', [])); result = original_box(ax, x, *args, **kwargs)
        values = samples(x); records = getattr(ax, '_fam_boxes', [])[before:]
        if len(values) == len(records):
            for record, value in zip(records, values): record['samples'] = value
        return result
    def violinplot(ax, dataset, *args, **kwargs):
        result = original_violin(ax, dataset, *args, **kwargs)
        import inspect
        bound = inspect.signature(original_violin).bind(ax, dataset, *args, **kwargs); bound.apply_defaults()
        horizontal = bound.arguments.get('orientation') == 'horizontal' or bound.arguments.get('vert') is False
        ax._fam_violins = getattr(ax, '_fam_violins', []) + [{'result': result, 'samples': samples(dataset), 'horizontal': horizontal}]
        return result
    Axes.boxplot, Axes.bxp, Axes.violinplot = boxplot, bxp, violinplot
    try: yield
    finally: Axes.boxplot, Axes.bxp, Axes.violinplot = original_box, original_bxp, original_violin


def recover(fig, fresh):
    """Attach known demo/dataset source inputs to old caches after geometry matches."""
    if len(fig.axes) != len(fresh.axes): return
    for ax, candidate in zip(fig.axes, fresh.axes):
        if hasattr(ax, '_fam_boxes'): continue
        records = getattr(candidate, '_fam_boxes', [])
        current = {a.get_gid(): a for a in list(ax.lines)+list(ax.patches)+list(ax.collections)}
        valid = []
        for record in records:
            parts = {}; matches = True
            for role, artists in record['parts'].items():
                parts[role] = []
                for artist in artists:
                    target = current.get(artist.get_gid())
                    if target is None: matches = False; break
                    def geometry(a): return a.get_path().vertices if hasattr(a, 'get_path') else np.column_stack(a.get_data(orig=False))
                    v, w = geometry(artist), geometry(target)
                    if v.shape != w.shape or not np.allclose(v, w, equal_nan=True): matches = False; break
                    parts[role].append(target)
            if not matches: break
            valid.append({**record, 'parts': parts})
        if len(valid) == len(records) and valid: ax._fam_boxes = valid
        # Violin metadata is used only for raw point overlays, after body equality.
        if not hasattr(ax, '_fam_violins'):
            values = []
            for record in getattr(candidate, '_fam_violins', []):
                mapped = {key: [current.get(a.get_gid()) for a in value] if isinstance(value, list) else current.get(value.get_gid())
                          for key, value in record['result'].items()}
                if all(a is not None for value in mapped.values() for a in (value if isinstance(value, list) else [value])):
                    if all(np.allclose(a.get_paths()[0].vertices, b.get_paths()[0].vertices) for a,b in zip(mapped['bodies'],record['result']['bodies'])):
                        values.append({**record, 'result': mapped})
            if values: ax._fam_violins = values


def stats_for(record, settings):
    values = record['samples']; source = copy.deepcopy(record['stats'])
    range_mode, whisker = settings.get('range', 'original'), settings.get('whiskers', 'original')
    if range_mode == 'original' and whisker == 'original': return source
    if values is None or not len(values): raise ValueError('改变箱区间或须线计算需要原始样本；请从原绘图脚本重新导入')
    stats = cbook.boxplot_stats(values)[0]
    stats['label'] = source.get('label', '')
    if range_mode in ('10-90', '5-95'): stats['q1'], stats['q3'] = np.percentile(values, [10,90] if range_mode=='10-90' else [5,95])
    elif range_mode == 'mean-sd':
        mean = float(np.mean(values)); sd = float(np.std(values, ddof=1)) if len(values)>1 else 0
        stats['q1'], stats['q3'] = mean-sd, mean+sd
    elif range_mode == 'original': stats['q1'], stats['q3'] = source['q1'], source['q3']
    if whisker == 'original':
        stats['whislo'], stats['whishi'] = min(source['whislo'],stats['q1']), max(source['whishi'],stats['q3'])
    elif whisker == 'minmax': stats['whislo'], stats['whishi'] = float(np.min(values)), float(np.max(values))
    elif whisker == '5-95':
        low, high = np.percentile(values, [5,95]); stats['whislo'], stats['whishi'] = min(low,stats['q1']), max(high,stats['q3'])
    else:
        iqr=stats['q3']-stats['q1']; low=values[values>=stats['q1']-1.5*iqr]; high=values[values<=stats['q3']+1.5*iqr]
        stats['whislo']=min(float(np.min(low)),stats['q1']); stats['whishi']=max(float(np.max(high)),stats['q3'])
    stats['fliers'] = values[(values<stats['whislo'])|(values>stats['whishi'])]
    return stats


def box_geometry(record):
    box = record['parts']['box'][0]
    v = box.get_path().vertices if hasattr(box, 'get_path') else np.column_stack(box.get_data(orig=False))
    dim = 1 if record['horizontal'] else 0
    return float((v[:,dim].min()+v[:,dim].max())/2), float(np.ptp(v[:,dim]))


def apply(fig, native):
    for key in native.get('boxPlots',{}):
        if not key.isdigit() or int(key)>=len(fig.axes) or not getattr(fig.axes[int(key)],'_fam_boxes',[]):raise ValueError('该坐标区域没有已接入统计量的箱线图')
    known={r['parts']['box'][0].get_gid() for ax in fig.axes for r in getattr(ax,'_fam_boxes',[])}
    if set(native.get('boxStyles',{}))-known:raise ValueError('箱线细节对应的箱体已变化，请重新选择')
    for ai, ax in enumerate(fig.axes):
        settings = native.get('boxPlots', {}).get(str(ai), {})
        for record in getattr(ax, '_fam_boxes', []):
            if not settings: continue
            values=record['samples']; stats=stats_for(record, settings); center, width=box_geometry(record)
            point_mode=settings.get('points','original'); center_mode=settings.get('center','original')
            if values is None and point_mode in ('all','outside-box'): raise ValueError('显示全部点或箱外点需要原始样本；请从原绘图脚本重新导入')
            parts=record['parts']; original_box=parts['box'][0]; gid=original_box.get_gid()
            # R-built jitter is captured as ordinary editable points. Hide it only
            # when replacing the point display; other box edits retain the points.
            for artist in record.get('sampleArtists',[]):
                if point_mode!='original':artist.set_visible(False)
            if point_mode=='none': stats['fliers']=[]
            elif point_mode in ('all','outside-box'):
                stats['fliers']=values if point_mode=='all' else values[(values<stats['q1'])|(values>stats['q3'])]
            elif point_mode=='original' and not parts.get('points'): stats['fliers']=[]
            elif point_mode=='original':stats['fliers']=np.asarray(parts['points'][0].get_xdata() if record['horizontal'] else parts['points'][0].get_ydata(),dtype=float)
            show_mean=bool(parts.get('mean')) if center_mode=='original' else center_mode in ('mean','both')
            if show_mean and 'mean' not in stats: raise ValueError('原始图没有均值统计量；请提供原始样本后重绘')
            notch=settings.get('notched',record['notched'])
            if notch and settings.get('range','original') not in ('original','quartile'): raise ValueError('凹口仅适用于四分位箱区间')
            if notch and not all(k in stats for k in ('cilo','cihi')):raise ValueError('中位数凹口需要已捕获的置信区间或原始样本')
            original_artists={role:list(artists) for role,artists in parts.items()}
            dim=1 if record['horizontal'] else 0
            cap_width=float(np.ptp(np.asarray(parts['cap'][0].get_data())[dim])) if parts.get('cap') else width/2
            for artists in original_artists.values():
                for artist in artists: artist.remove()
            result=ax.bxp([stats],positions=[center],widths=[settings.get('width',width)],orientation='horizontal' if record['horizontal'] else 'vertical',
                          patch_artist=record['patch'],shownotches=notch,showmeans=show_mean,meanline=settings.get('meanStyle','line' if record.get('meanline') else 'point')=='line',
                          showfliers=True,manage_ticks=False,showcaps=bool(parts.get('cap')),capwidths=[cap_width*settings.get('width',width)/width])
            newparts={'box':result['boxes'],'median':result['medians'],'mean':result['means'],'whisker':result['whiskers'],'cap':result['caps'],'points':result['fliers']}
            for role, artists in newparts.items():
                for j,artist in enumerate(artists):
                    old=original_artists.get(role,[])
                    if j<len(old):
                        artist.set_gid(old[j].get_gid())
                        for getter,setter in [('get_color','set_color'),('get_facecolor','set_facecolor'),('get_edgecolor','set_edgecolor'),('get_linewidth','set_linewidth'),('get_alpha','set_alpha'),('get_linestyle','set_linestyle'),('get_marker','set_marker'),('get_markersize','set_markersize'),('get_markeredgewidth','set_markeredgewidth'),('get_markerfacecolor','set_markerfacecolor'),('get_markeredgecolor','set_markeredgecolor'),('get_hatch','set_hatch'),('get_zorder','set_zorder')]:
                            if hasattr(old[j],getter) and hasattr(artist,setter):getattr(artist,setter)(getattr(old[j],getter)())
                        artist.set_visible(old[j].get_visible())
                    else: artist.set_gid(f'{gid}-{role}-{j}')
            if show_mean and 'meanStyle' in settings:
                for artist in newparts['mean']:
                    artist.set_linestyle('--' if settings['meanStyle']=='line' else 'none');artist.set_marker('' if settings['meanStyle']=='line' else 'D')
            if center_mode!='original':
                for artist in newparts['median']:artist.set_visible(center_mode in ('median','both'))
                for artist in newparts['mean']:artist.set_visible(center_mode in ('mean','both'))
            if center_mode in ('none','mean'):
                for artist in newparts['median']: artist.set_visible(False)
            if point_mode=='original' and 'jitter' not in settings and original_artists.get('points') and newparts.get('points'):
                newparts['points'][0].set_data(*original_artists['points'][0].get_data())
            jitter=float(settings.get('jitter',0))
            if jitter and point_mode in ('all','outside-box','outliers'):
                for artist in newparts['points']:
                    x,y=artist.get_data(); count=len(x); shift=np.random.default_rng(20261007).uniform(-jitter,jitter,count)*settings.get('width',width)
                    artist.set_data(x,y+shift) if record['horizontal'] else artist.set_data(x+shift,y)
            record['parts']=newparts
            # Keep the source statistics and samples unchanged for reproducible rebuilds.
        for record in getattr(ax,'_fam_boxes',[]):
            gid=record['parts']['box'][0].get_gid()
            for role,style in native.get('boxStyles',{}).get(gid,{}).items():
                for artist in record['parts'].get(role,[]): apply_style(artist,style)


def update_demo_caption(fig,native):
    """Update only the exact instructional caption of the known box template."""
    if getattr(fig,'_fam_paper_kind',None)!='box':return
    p=native.get('boxPlots',{}).get('0',{})
    if not set(p)&{'range','whiskers','center','meanStyle','points','notched'}:return
    original='Box = Q1–Q3; center = median; whiskers = 1.5 IQR; all 48 demo values shown per group.'
    span=p.get('range','original');box={'original':'Q1–Q3','quartile':'Q1–Q3','10-90':'P10–P90','5-95':'P5–P95','mean-sd':'mean ± sample SD'}[span]
    center={'original':'median','median':'median','mean':'mean','both':'median + mean','none':'hidden'}[p.get('center','original')]
    if p.get('center') in ('mean','both'):center+=' ('+p.get('meanStyle','point')+')'
    whisker={'original':'1.5 IQR' if span in ('original','quartile') else 'source limits, covering box','iqr':'1.5 × box span','minmax':'min–max','5-95':'P5–P95, covering box'}[p.get('whiskers','original')]
    points={'original':'all captured values','all':'all values','none':'hidden','outside-box':'outside box','outliers':'outside whiskers'}[p.get('points','original')]
    note=f'Box = {box}; center = {center}; whiskers = {whisker}.\nDemo points: {points}'+('; median notches shown' if p.get('notched') else '')+'. Source samples preserved.'
    fig._fam_display_note=note
    for text in fig.texts:
        if text.get_text()!=original:continue
        text.set_text(note)
        for watermark in fig.texts:
            if watermark.get_text()=='SYNTHETIC DEMONSTRATION':
                watermark.set_y(text.get_position()[1]+(text.get_fontsize()*2.4+watermark.get_fontsize()*.6)/(fig.get_figheight()*72))


def apply_style(artist, style):
    from adjustments import apply_series_colors
    apply_series_colors(artist, style)
    for key,setter in [('lineWidth','set_linewidth'),('markerSize','set_markersize'),('lineStyle','set_linestyle'),('visible','set_visible')]:
        if key in style and hasattr(artist,setter): getattr(artist,setter)(style[key])


def describe(fig):
    result=[]
    for ai,ax in enumerate(fig.axes):
        records=getattr(ax,'_fam_boxes',[])
        if records: result.append({'axis':ai,'kind':'box','count':len(records),'raw':all(r['samples'] is not None for r in records),
                                   'boxes':[{'artist':r['parts']['box'][0].get_gid(),'width':box_geometry(r)[1],'horizontal':r['horizontal'],'notched':r['notched'],'meanline':r.get('meanline',False),
                                             'components':{role:[style_of(a) for a in artists] for role,artists in r['parts'].items() if role!='box'}} for r in records]})
    return result


def style_of(artist):
    from adjustments import hex_color
    color=artist.get_color() if hasattr(artist,'get_color') else artist.get_edgecolor()
    result={'color':hex_color(color),'alpha':artist.get_alpha() if artist.get_alpha() is not None else to_rgba(color)[3],
            'lineWidth':float(artist.get_linewidth()),'visible':artist.get_visible()}
    for key,getter in [('markerSize','get_markersize'),('edgeWidth','get_markeredgewidth')]:
        if hasattr(artist,getter):result[key]=float(getattr(artist,getter)())
    if hasattr(artist,'get_markeredgecolor'):
        edge=artist.get_markeredgecolor();result['edgeColor']=hex_color(color if isinstance(edge,str) and edge=='auto' else edge)
    return result


def validate(native):
    from adjustments import finite
    choices={'points':('original','none','all','outside-box','outliers'),'center':('original','median','mean','both','none'),
             'range':('original','quartile','10-90','5-95','mean-sd'),'whiskers':('original','iqr','minmax','5-95'),'meanStyle':('point','line')}
    for key,p in native.get('boxPlots',{}).items():
        if not key.isdigit():raise ValueError('箱线图坐标区域无效')
        for key,allowed in choices.items():
            if key in p and p[key] not in allowed: raise ValueError('未知箱线图画法：'+key)
        if 'width' in p: finite(p['width'],.001,100)
        if 'jitter' in p: finite(p['jitter'],0,.5)
        if 'notched' in p and not isinstance(p['notched'],bool): raise ValueError('箱线凹口参数须为布尔值')
    for parts in native.get('boxStyles',{}).values():
        for role,style in parts.items():
            if role not in ('median','mean','whisker','cap','points'): raise ValueError('未知箱线图组件')
            for key in ('color','edgeColor'):
                if key in style:to_rgba(style[key])
            for key in ('lineWidth','markerSize','alpha'):
                if key in style:finite(style[key],0,1 if key=='alpha' else 100)
