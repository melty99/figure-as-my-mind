"""Display-only major tick policies, evaluated against the effective axis range."""
import math
import numpy as np
from matplotlib import ticker
MAX_TICKS=200

def number(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)

def validate(policy):
    if not isinstance(policy,dict) or policy.get('mode') not in ('auto','interval','count','manual'):raise ValueError('主刻度方式无效')
    mode=policy['mode']
    if mode=='interval' and (not number(policy.get('interval')) or policy['interval']<=0):raise ValueError('主刻度间隔必须是有限正数')
    if mode=='count' and (not number(policy.get('count')) or int(policy['count'])!=policy['count'] or not 2<=policy['count']<=MAX_TICKS):raise ValueError('主刻度数量须为 2–200 的整数（包含两端）')
    if mode=='manual':
        values=policy.get('values')
        if not isinstance(values,list) or not 1<=len(values)<=MAX_TICKS or not all(number(v) for v in values) or len(set(values))!=len(values):raise ValueError('自定义主刻度须为 1–200 个互不重复的有限数值')

def axis_type(axis):
    locator=axis.get_major_locator();formatter=axis.get_major_formatter()
    modules=' '.join(type(o).__module__ for o in [locator,formatter,axis.get_converter() if hasattr(axis,'get_converter') else getattr(axis,'converter',None)])
    if 'matplotlib.dates' in modules:return 'date'
    if 'matplotlib.category' in modules:return 'categorical'
    if isinstance(locator,ticker.FixedLocator) and isinstance(formatter,(ticker.FixedFormatter,ticker.FuncFormatter)):
        labels=formatter.format_ticks(locator.locs)
        try:
            for label in labels:
                text=str(label).strip() if label is not None else ''
                if text:float(text.replace('−','-').replace(',', ''))
        except (ValueError,TypeError):return 'categorical'
    return 'numeric'

def positions(axis,policy):
    validate(policy);mode=policy['mode'];lo,hi=sorted(map(float,axis.get_view_interval()))
    if mode=='manual':values=np.array(sorted(policy['values']),dtype=float)
    elif mode=='interval':
        step=policy['interval'];q0,q1=lo/step,hi/step
        if not math.isfinite(q0) or not math.isfinite(q1) or max(abs(q0),abs(q1))>1e14:raise ValueError('主刻度间隔过小，请增大间隔')
        start=math.ceil(q0-1e-10);stop=math.floor(q1+1e-10);count=max(0,stop-start+1)
        if count>MAX_TICKS:raise ValueError('主刻度超过 200 个，请增大间隔')
        values=np.array([(start+i)*step for i in range(count)],dtype=float)
        if len(values):values[np.abs(values)<step*1e-10]=0
    elif mode=='count':
        n=int(policy['count']);transform=axis.get_transform();ends=np.asarray(transform.transform(np.array([lo,hi])));t=np.linspace(0,1,n);values=np.asarray(transform.inverted().transform((1-t)*ends[0]+t*ends[1]),dtype=float);values[0]=lo;values[-1]=hi
    else:return None
    if not np.all(np.isfinite(values)) or len(np.unique(values))!=len(values):raise ValueError('主刻度精度不足，请减少数量或增大间隔')
    return values

def apply(ax,dim,patch):
    key=dim+'majorTicks';axis=getattr(ax,dim+'axis')
    if key not in patch:
        if dim+'ticks' in patch:getattr(ax,'set_'+dim+'ticks')(patch[dim+'ticks'])
        return False
    policy=patch[key];validate(policy)
    if policy['mode']=='auto':return True
    if axis_type(axis)!='numeric':raise ValueError('分类或日期轴请保留原刻度，在原绘图代码中调整分类或日期间隔')
    formatter=axis.get_major_formatter();locator=axis.get_major_locator()
    replace_formatter=isinstance(formatter,(ticker.LogFormatter,ticker.FixedFormatter)) or isinstance(formatter,ticker.FuncFormatter) and isinstance(locator,ticker.FixedLocator)
    axis.set_major_locator(ticker.FixedLocator(positions(axis,policy)))
    if replace_formatter:axis.set_major_formatter(ticker.StrMethodFormatter('{x:.12g}'))
    return True

def describe(ax):
    out={}
    for dim in ('x','y','z'):
        axis=getattr(ax,dim+'axis',None)
        if axis is None:continue
        lo,hi=sorted(axis.get_view_interval());values=[float(v) for v in axis.get_majorticklocs() if math.isfinite(v) and lo-abs(hi-lo)*1e-10<=v<=hi+abs(hi-lo)*1e-10][:MAX_TICKS]
        out[dim]={'type':axis_type(axis),'values':values}
    return out
