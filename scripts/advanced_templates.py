"""Four distinct scientific chart types with explicit, synthetic input tables."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
CATALOG=[('dotplot','堆叠点图','等宽分箱内每个点表示一个观测'),('dumbbell','哑铃图','每个类别的两个端点及其变化'),('mosaic','马赛克图','矩形面积表示列联表的计数比例'),('parallel-coordinates','平行坐标图','同一样本的多个变量连接轮廓')]
REFERENCES={'dotplot':'https://ggplot2.tidyverse.org/reference/geom_dotplot.html','dumbbell':'https://ggplot2.tidyverse.org/reference/geom_segment.html','mosaic':'https://www.stat.math.ethz.ch/R-manual/R-devel/library/graphics/html/mosaicplot.html','parallel-coordinates':'https://pandas.pydata.org/docs/reference/api/pandas.plotting.parallel_coordinates.html'}
COLORS=['#0072b2','#d55e00','#009e73','#cc79a7']

def build(kind,title=None):
    rng=np.random.default_rng(20261012);fig,ax=plt.subplots(figsize=(7,5));fig.subplots_adjust(left=.18,right=.93,bottom=.18,top=.84)
    data={};info={};names={k:n for k,n,_ in CATALOG}
    if kind=='dotplot':
        values=np.r_[rng.normal(-.3,.55,45),rng.normal(1.1,.4,35)];width=.16;bins=np.round(values/width).astype(int);counts={};offset=[]
        for b in bins:offset.append(counts.get(b,0));counts[b]=counts.get(b,0)+1
        artist=ax.scatter(bins*width,np.array(offset)+.5,s=28,color=COLORS[0],edgecolors='white',lw=.4)
        rows=[{'id':f'D{i+1:03d}','value':float(v),'binCenter':float(b*width)} for i,(v,b) in enumerate(zip(values,bins))];artist._fam_sample_ids=[r['id'] for r in rows];artist._fam_sample_rows=rows
        ax.set(xlabel='Value',ylabel='Stack count',ylim=(0,max(offset)+1.5));data={'samples':rows,'binWidth':width};info={'artist':artist,'values':values}
    elif kind=='dumbbell':
        a=rng.uniform(12,35,8);b=a+rng.uniform(-4,16,8);y=np.arange(8);lines=[]
        for i in range(8):
            line=ax.plot([a[i],b[i]],[i,i],color='#b8c9d1',lw=2,zorder=1)[0];line._fam_independent=True;line._fam_observation_exclude=True;lines.append(line)
        collections=[]
        for j,v in enumerate([a,b]):
            artist=ax.scatter(v,y,s=45,color=COLORS[j],edgecolors='white',lw=.6,label=['Before','After'][j],zorder=2);rows=[{'id':f'C{i+1}-{j}','category':f'Category {i+1}','condition':['Before','After'][j],'value':float(x)} for i,x in enumerate(v)];artist._fam_sample_ids=[r['id'] for r in rows];artist._fam_sample_rows=rows;collections.append(artist)
        ax.set_yticks(y,[f'Category {i+1}' for i in y]);ax.set_xlabel('Value');ax.legend(frameon=False,ncols=2);data={'before':a.tolist(),'after':b.tolist(),'categories':[f'Category {i+1}' for i in y]};info={'collections':collections,'lines':lines}
        fig._fam_dumbbell_links=info
    elif kind=='mosaic':
        counts=rng.integers(8,60,(4,3));totals=counts.sum(axis=1);cursor=0;patches=[];labels=[]
        for i,total in enumerate(totals):
            width=total/counts.sum();bottom=0
            for j,count in enumerate(counts[i]):
                height=count/total;rect=Rectangle((cursor,bottom),width,height,facecolor=COLORS[j],edgecolor='white',lw=1.5);rect._fam_independent=True;ax.add_patch(rect);patches.append(rect)
                labels.append(ax.text(cursor+width/2,bottom+height/2,str(count),ha='center',va='center',fontsize=9,color='white'));bottom+=height
            ax.text(cursor+width/2,-.06,f'Group {chr(65+i)}',ha='center',va='top',fontsize=9);cursor+=width
        ax.set(xlim=(0,1),ylim=(0,1),ylabel='Within-group proportion');ax.set_xticks([]);ax.legend(handles=[Rectangle((0,0),1,1,color=COLORS[j],label=f'Class {j+1}') for j in range(3)],frameon=False,ncols=3,loc='upper center',bbox_to_anchor=(.5,1.15))
        data={'counts':counts.tolist(),'groups':[f'Group {chr(65+i)}' for i in range(4)],'classes':[f'Class {j+1}' for j in range(3)]};info={'labels':labels}
    elif kind=='parallel-coordinates':
        values=rng.normal(size=(18,5));groups=np.arange(18)//6;values+=groups[:,None]*.7;low=values.min(axis=0);high=values.max(axis=0);normal=(values-low)/(high-low);lines=[]
        for i,row in enumerate(normal):
            line=ax.plot(range(5),row,color=COLORS[groups[i]],lw=1.1,alpha=.6,label=f'Group {chr(65+groups[i])}' if i%6==0 else '_nolegend_')[0];line._fam_sample_ids=[f'S{i+1}-V{j+1}' for j in range(5)];line._fam_sample_rows=[{'sample':f'S{i+1}','variable':f'V{j+1}','value':float(values[i,j])} for j in range(5)];lines.append(line)
        for x in range(5):
            line=ax.axvline(x,color='#e2e9ed',lw=.7,zorder=0);line._fam_independent=True;line._fam_observation_exclude=True
        ax.set_xticks(range(5),[f'V{i+1}' for i in range(5)]);ax.set(xlabel='Variable',ylabel='Column min–max scaled value',ylim=(-.03,1.03));ax.legend(frameon=False,ncols=3)
        data={'values':values.tolist(),'groups':groups.tolist(),'minimum':low.tolist(),'maximum':high.tolist()};info={'lines':lines,'values':values,'normalized':normal}
    else:raise ValueError('未知图型')
    fig.suptitle(title or names[kind],fontfamily='Microsoft YaHei',fontsize=13,y=.96);fig._fam_template_data=data;fig._fam_advanced_info=info;fig._fam_paper_kind=kind;fig._fam_template_edition='single-v3';return fig

def apply(fig,p):
    info=getattr(fig,'_fam_advanced_info',{});kind=getattr(fig,'_fam_graphkind',None)
    if kind=='dotplot' and 'dotBinWidth' in p:
        values=info['values'];width=p['dotBinWidth'];bins=np.round(values/width).astype(int);counts={};offset=[]
        for b in bins:offset.append(counts.get(b,0));counts[b]=counts.get(b,0)+1
        fig.axes[0].set_ylim(0,max(offset)+1.5);info['artist'].set_offsets(np.column_stack([bins*width,np.array(offset)+.5]))
    if kind=='mosaic' and 'mosaicLabels' in p:
        for text in info.get('labels',[]):text.set_visible(p['mosaicLabels'])
    if kind=='parallel-coordinates' and 'parallelNormalize' in p:
        values=info['normalized'] if p['parallelNormalize'] else info['values']
        for line,row in zip(info['lines'],values):line.set_ydata(row)
        fig.axes[0].set_ylabel('Column min–max scaled value' if p['parallelNormalize'] else 'Original value');fig.axes[0].set_ylim(values.min()-.05*np.ptp(values),values.max()+.05*np.ptp(values))

def bind(graph):
    info=getattr(graph.fig,'_fam_dumbbell_links',None)
    if not info:return
    for j,collection in enumerate(info['collections']):
        for i,line in enumerate(info['lines']):
            e=graph.entities.get(f'{collection.get_gid()}::p{i}')
            if e:e['links'].append({'artist':line,'index':j,'role':'network-edge','position':np.column_stack(line.get_data()).copy()})

def validate(p):
    from adjustments import finite
    if 'dotBinWidth' in p:finite(p['dotBinWidth'],.001,1e6)
    for key in ('mosaicLabels','parallelNormalize'):
        if key in p and not isinstance(p[key],bool):raise ValueError('画法开关需要布尔值')
