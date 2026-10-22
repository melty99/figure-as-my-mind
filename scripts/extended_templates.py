"""Additional scientific chart geometries computed from explicit demo inputs."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Wedge
from scipy import stats
from publication_design import COLORS

SEED=20261011
CATALOG=[
 ('raincloud','雨云图','样本、半密度与四分位汇总'),
 ('paired','配对变化图','同一 ID 的前后观测与连线'),
 ('estimation','效应量估计图','原始样本、差值与 bootstrap 区间'),
 ('hexbin','六边形分箱图','密集观测、分箱计数与色标'),
 ('correlation','相关矩阵图','配对相关、系数与有效样本数'),
 ('pca-biplot','PCA 双标图','样本得分与明确缩放的变量载荷'),
 ('ma','MA 图','平均丰度、变化幅度与显著条目'),
 ('decision-curve','决策曲线图','阈值概率、净获益与参考策略'),
 ('cumulative-incidence','累积发生率图','竞争事件与 Aalen–Johansen 累积发生率'),
 ('nomogram','列线图','已知模型系数、分值与预测概率'),
 ('circular-tracks','多轨道环形图','共同扇区内的连续轨道与标签'),
 ('interval-tracks','区间轨道图','共享位置轴的区间、方向与信号')]
REFERENCES={
 'raincloud':'https://pmc.ncbi.nlm.nih.gov/articles/PMC6480976/',
 'paired':'https://r-graph-gallery.com/web-dumbell-chart.html',
 'estimation':'https://acclab.github.io/DABEST-python/tutorials/01-basics.html',
 'hexbin':'https://ggplot2.tidyverse.org/reference/geom_hex.html',
 'correlation':'https://r-graph-gallery.com/correlogram.html',
 'pca-biplot':'https://factoextra.net/intro.html',
 'ma':'https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html',
 'decision-curve':'https://www.danieldsjoberg.com/dcurves/articles/dca.html',
 'cumulative-incidence':'https://cran.r-project.org/web/packages/survival/vignettes/compete.pdf',
 'nomogram':'https://hbiostat.org/r/rms/',
 'circular-tracks':'https://jokergoo.github.io/circlize_book/book/circular-layout.html',
 'interval-tracks':'https://bioconductor.org/packages/release/bioc/vignettes/Gviz/inst/doc/Gviz.html'}

def input_data(kind,rng):
    if kind in ('raincloud','paired','estimation'):
        a=rng.normal(5,1,48);b=a+rng.normal(.7,.6,48)
        return {'ids':[f'S{i+1:03}' for i in range(48)],'before':a.tolist(),'after':b.tolist(),'paired':True}
    if kind=='hexbin':
        a=rng.multivariate_normal([0,0],[[1,.7],[.7,1]],6000)
        return {'x':a[:,0].tolist(),'y':a[:,1].tolist()}
    if kind in ('correlation','pca-biplot'):
        x=rng.normal(size=(90,6));x[:,1]=.8*x[:,0]+rng.normal(0,.5,90);x[30:60,:3]+=1.5;x[60:,:3]-=1
        return {'matrix':x.tolist(),'variables':[f'V{i+1}' for i in range(6)],'groups':['Group '+chr(65+i//30) for i in range(90)]}
    if kind=='ma':
        mean=np.exp(rng.uniform(1,10,500));effect=rng.normal(0,1/np.sqrt(np.log1p(mean)),500);effect[:20]+=rng.choice([-1,1],20)*1.5
        p=2*stats.norm.sf(abs(effect)*np.sqrt(np.log1p(mean)));order=np.argsort(p);q=np.empty(500);q[order]=np.minimum.accumulate((p[order]*500/np.arange(1,501))[::-1])[::-1].clip(0,1)
        return {'mean':mean.tolist(),'effect':effect.tolist(),'q':q.tolist(),'labels':[f'G{i+1}' for i in range(500)],'method':'Synthetic normal z model and BH; not DESeq2 analysis'}
    if kind=='decision-curve':
        score=stats.special.expit(rng.normal(size=300)) if hasattr(stats,'special') else 1/(1+np.exp(-rng.normal(size=300)))
        y=(rng.random(300)<score).astype(int)
        return {'outcome':y.tolist(),'scores':[score.tolist(),np.clip(score+rng.normal(0,.16,300),.001,.999).tolist()]}
    if kind=='cumulative-incidence':
        e1=rng.exponential(18,240);e2=rng.exponential(30,240);c=rng.uniform(6,36,240)
        t=np.minimum.reduce([e1,e2,c]);event=np.where(t==c,0,np.where(e1<e2,1,2))
        return {'time':t.tolist(),'event':event.tolist(),'groups':['Group '+chr(65+i//120) for i in range(240)]}
    if kind=='nomogram':return {'coefficients':[.045,1.1,-.7],'intercept':-3.2,'variables':['Age','Marker','Condition'],'ranges':[[20,80],[0,2],[0,1]],'model':'Declared synthetic logistic model; not a clinical model'}
    if kind=='circular-tracks':return {'values':rng.uniform(0,1,(3,24)).tolist(),'sectors':['A','B','C','D'],'tracks':['Abundance','Change','Signal']}
    if kind=='interval-tracks':return {'intervals':[[5,18,1],[24,38,-1],[45,56,1],[63,78,-1],[84,96,1]],'signal':(np.sin(np.linspace(0,8,200))*.3+.5).tolist()}
    raise ValueError(kind)

def cumulative_incidence(times,events):
    times=np.asarray(times,float);events=np.asarray(events,int)
    if len(times)!=len(events) or not len(times) or not np.isfinite(times).all() or (times<0).any() or not np.isin(events,[0,1,2]).all():raise ValueError('竞争事件需要有效 time 和 event=0/1/2')
    survival=1.;risk=[];f=np.zeros(2);values=[[0.,0.]];grid=[0.]
    for t in np.unique(times):
        at_risk=np.sum(times>=t);counts=np.array([np.sum((times==t)&(events==k)) for k in (1,2)])
        f+=survival*counts/at_risk;survival*=1-counts.sum()/at_risk
        grid.append(float(t));values.append(f.copy());risk.append(int(at_risk))
    return np.array(grid),np.array(values),risk

def net_benefit(y,score,thresholds):
    y=np.asarray(y);score=np.asarray(score);thresholds=np.asarray(thresholds)
    if len(y)!=len(score) or not np.isin(y,[0,1]).all() or not np.isfinite(score).all() or ((score<0)|(score>1)).any() or ((thresholds<=0)|(thresholds>=1)).any():raise ValueError('净获益需要二元结局、概率以及 0–1 内的阈值')
    positive=score[:,None]>=thresholds
    return ((positive&(y[:,None]==1)).sum(0)-(positive&(y[:,None]==0)).sum(0)*thresholds/(1-thresholds))/len(y)

def build(kind,title=None,data=None):
    rng=np.random.default_rng(SEED);data=data or input_data(kind,rng)
    with plt.rc_context({'font.family':['Arial','Microsoft YaHei'],'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'}):
        fig=plt.figure(figsize=(7.2,5.2));ax=fig.add_subplot(111,projection='polar' if kind=='circular-tracks' else None)
        fig.subplots_adjust(left=.17,right=.9,bottom=.16,top=.85)
        if kind=='raincloud':
            for i,key in enumerate(('before','after')):
                values=np.asarray(data[key]);grid=np.linspace(values.min()-.5,values.max()+.5,150);density=stats.gaussian_kde(values)(grid);density=density/density.max()*.34
                ax.fill_betweenx(grid,i,i+density,color=COLORS[i],alpha=.35,lw=.7)
                ax.scatter(i-rng.uniform(.1,.32,len(values)),values,s=15,color=COLORS[i],alpha=.65,edgecolors='white',linewidths=.3,label=key.title())
                b=ax.boxplot([values],positions=[i+.045],widths=.09,patch_artist=True,showfliers=False)
                b['boxes'][0].set_facecolor('white');b['medians'][0].set_color('#343A40')
            ax.set(xticks=[0,1],xticklabels=['Before','After'],ylabel='Response',xlim=(-.45,1.5))
        elif kind=='paired':
            a,b=np.asarray(data['before']),np.asarray(data['after'])
            pairs=[];observations=[]
            for i,(x,y) in enumerate(zip(a,b)):
                line=ax.plot([0,1],[x,y],color='#AEB9C2',alpha=.55,lw=.7)[0];line._fam_sample_id=data['ids'][i]
                line._fam_fit_exclude=True
                line._fam_observation_exclude=True;pairs.append(line)
            for i,(values,name) in enumerate(((a,'Before'),(b,'After'))):
                points=ax.scatter(np.full(len(values),i),values,color=COLORS[i],s=25,edgecolors='white',linewidths=.4,label=name);points._fam_sample_ids=data['ids']
                observations.append(points)
            for i,line in enumerate(pairs):line._fam_vertex_bindings=[(observations[0],i,0),(observations[1],i,1)]
            ax.set(xticks=[0,1],xticklabels=['Before','After'],ylabel='Response',xlim=(-.3,1.3));ax.legend(frameon=False)
        elif kind=='estimation':
            a,b=np.asarray(data['before']),np.asarray(data['after']);difference=b-a
            boot=np.mean(rng.choice(difference,(3000,len(difference)),replace=True),axis=1);lo,hi=np.quantile(boot,[.025,.975])
            ax.scatter(rng.uniform(-.08,.08,len(a)),a,s=18,c=COLORS[0],alpha=.6);ax.scatter(1+rng.uniform(-.08,.08,len(b)),b,s=18,c=COLORS[1],alpha=.6)
            ax.set(xticks=[0,1],xticklabels=['Before','After'],ylabel='Response');ax.set_position([.14,.17,.37,.66])
            effect=fig.add_axes([.68,.17,.22,.66]);effect.violinplot([boot],positions=[0],showextrema=False)
            effect.errorbar([0],[difference.mean()],yerr=[[difference.mean()-lo],[hi-difference.mean()]],fmt='o',c=COLORS[1],capsize=4)
            effect.axhline(0,c='#AEB9C2',ls='--',lw=.8);effect.set(xticks=[0],xticklabels=['After − Before'],ylabel='Paired mean difference');data={**data,'effect':float(difference.mean()),'ci':[float(lo),float(hi)],'bootstrap':3000,'interval':'paired percentile bootstrap 95%'}
        elif kind=='hexbin':
            m=ax.hexbin(data['x'],data['y'],gridsize=38,mincnt=1,cmap='viridis',linewidths=0);fig.colorbar(m,ax=ax,label='Count');ax.set(xlabel='Predictor',ylabel='Response')
        elif kind=='correlation':
            x=np.asarray(data['matrix']);r=np.corrcoef(x,rowvar=False);mask=np.triu(np.ones_like(r,dtype=bool),1)
            image=ax.imshow(np.ma.array(r,mask=mask),cmap='RdBu_r',vmin=-1,vmax=1)
            for i in range(len(r)):
                for j in range(i+1):ax.text(j,i,f'{r[i,j]:.2f}',ha='center',va='center',fontsize=9,color='white' if abs(r[i,j])>.65 else '#263238')
            ax.set(xticks=range(len(r)),yticks=range(len(r)),xticklabels=data['variables'],yticklabels=data['variables']);fig.colorbar(image,ax=ax,label='Pearson r',shrink=.75);data={**data,'r':r.tolist(),'n':len(x),'method':'Pearson, complete finite demo rows'}
        elif kind=='pca-biplot':
            x=np.asarray(data['matrix']);z=(x-x.mean(0))/x.std(0,ddof=1);u,s,v=np.linalg.svd(z,full_matrices=False);scores=u[:,:2]*s[:2];factor=np.max(abs(scores))*.65;loads=v[:2].T*factor
            for i,g in enumerate(sorted(set(data['groups']))):
                sub=scores[np.array(data['groups'])==g];ax.scatter(*sub.T,s=24,color=COLORS[i],label=g,alpha=.7)
            for name,(x,y) in zip(data['variables'],loads):
                ax.annotate('',(x,y),xytext=(0,0),arrowprops={'arrowstyle':'->','color':'#626C75','lw':.8})
                ax.text(x*1.1,y*1.1,name,ha='center',fontsize=9)
            variance=s*s/(s*s).sum();ax.set(xlabel=f'PC1 ({variance[0]:.1%})',ylabel=f'PC2 ({variance[1]:.1%})');ax.legend(frameon=False,loc='upper right');data={**data,'scores':scores.tolist(),'loadings':v[:2].T.tolist(),'arrowDisplayFactor':float(factor),'variance':variance.tolist()}
        elif kind=='ma':
            mean,effect,q=np.asarray(data['mean']),np.asarray(data['effect']),np.asarray(data['q']);significant=q<.05
            for mask,color,label in [(~significant,'#B8C1C9','Other'),(significant,COLORS[1],'q < 0.05')]:ax.scatter(mean[mask],effect[mask],s=14,c=color,alpha=.65,label=label)
            ax.axhline(0,c='#67737D',lw=.8,ls='--');ax.set(xscale='log',xlabel='Mean abundance',ylabel='log2 change');ax.legend(frameon=False)
        elif kind=='decision-curve':
            t=np.linspace(.01,.8,120);y=np.asarray(data['outcome']);curves=[]
            for i,score in enumerate(data['scores']):
                nb=net_benefit(y,score,t);curves.append(nb.tolist());ax.plot(t,nb,color=COLORS[i],lw=1.5,label=f'Model {i+1}')
            ax.plot(t,np.full_like(t,0),c='#9CA6AE',ls=':',label='Treat none');ax.plot(t,y.mean()-(1-y.mean())*t/(1-t),c='#626C75',ls='--',label='Treat all')
            ax.set(xlabel='Threshold probability',ylabel='Net benefit',ylim=(-.1,max(y.mean(),.3)+.05));ax.legend(frameon=False);data={**data,'thresholds':t.tolist(),'netBenefit':curves}
        elif kind=='cumulative-incidence':
            for i,g in enumerate(sorted(set(data['groups']))):
                mask=np.array(data['groups'])==g;t,values,_=cumulative_incidence(np.array(data['time'])[mask],np.array(data['event'])[mask])
                for j in range(2):ax.step(t,values[:,j],where='post',c=COLORS[i],ls=['-','--'][j],label=f'{g} · Event {j+1}',lw=1.4)
            ax.set(xlabel='Time',ylabel='Cumulative incidence',ylim=(0,1));ax.legend(frameon=False);data={**data,'method':'Aalen–Johansen; events at tied times before censor removal'}
        elif kind=='nomogram':
            co=np.asarray(data['coefficients']);ranges=np.asarray(data['ranges']);width=np.abs(co)*(ranges[:,1]-ranges[:,0]);unit=width.max()/100
            for i,(name,c,r) in enumerate(zip(data['variables'],co,ranges)):
                values=np.linspace(*r,2 if name=='Condition' else 5);points=(values-r.min())*abs(c)/unit
                if c<0:points=points[::-1]
                ax.plot([0,width[i]/unit],[4-i,4-i],c='#67737D',lw=.8)
                for point,value in zip(points,values):ax.plot([point,point],[4-i-.06,4-i+.06],c='#67737D',lw=.7);ax.text(point,4-i-.16,f'{value:g}',ha='center',fontsize=8)
                ax.text(-8,4-i,name,ha='right',va='center')
            baseline=data['intercept']+sum(c*(r[0] if c>=0 else r[1]) for c,r in zip(co,ranges));total=np.linspace(0,width.sum()/unit,6)
            ax.plot([0,100],[4.8,4.8],c='#67737D',lw=.8);ax.text(-8,4.8,'Points',ha='right',va='center')
            for t in np.linspace(0,100,6):ax.text(t,4.64,f'{t:g}',ha='center',fontsize=8)
            ax.plot([0,total[-1]],[0,0],c='#67737D',lw=.8)
            for t in total:ax.text(t,-.18,f'{1/(1+np.exp(-(baseline+t*unit))):.2f}',ha='center',fontsize=8)
            ax.text(-8,0,'Probability',ha='right');ax.set(xlim=(-35,total[-1]+8),ylim=(-.5,5),yticks=[],xlabel='Points (100 points = largest variable contribution)');ax.spines[['left','bottom']].set_visible(False);ax.set_xticks([]);data={**data,'pointUnit':float(unit),'baseline':float(baseline)}
        elif kind=='circular-tracks':
            values=np.asarray(data['values']);count=values.shape[1];angles=np.arange(count)*2*np.pi/count
            fig._fam_track_bars=[]
            for j,row in enumerate(values):
                bars=ax.bar(angles,.27,bottom=.25+j*.32,width=2*np.pi/count*.9,color=plt.get_cmap('viridis')(row),edgecolor='white',lw=.4)
                for bar in bars:bar._fam_observation_exclude=True
                fig._fam_track_bars.append(list(bars))
            ax.set(xticks=np.arange(4)*np.pi/2+np.pi/4,xticklabels=data['sectors'],yticks=[]);ax.grid(False);ax.spines['polar'].set_visible(False);ax.set_ylim(0,1.3)
            from matplotlib.cm import ScalarMappable
            from matplotlib.colors import Normalize
            mappable=ScalarMappable(norm=Normalize(0,1),cmap='viridis');mappable.set_array(values);ax._fam_mappables=[mappable]
            fig._fam_track_mappable=mappable
            fig.colorbar(mappable,ax=ax,fraction=.035,pad=.13,label='Scaled value')
            for j,name in enumerate(data['tracks']):ax.text(np.pi/2,.25+j*.32+.13,name,ha='center',va='center',fontsize=7,bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':1})
        elif kind=='interval-tracks':
            for i,(start,end,direction) in enumerate(data['intervals']):
                ax.broken_barh([(start,end-start)],(1.7,.24),facecolors=COLORS[i%3]);ax.annotate('',(end if direction>0 else start,1.82),xytext=(start if direction>0 else end,1.82),arrowprops={'arrowstyle':'->','color':'white'});ax.text((start+end)/2,2.05,f'Region {i+1}',ha='center',fontsize=8)
            signal=np.asarray(data['signal']);grid=np.linspace(0,100,len(signal));ax.fill_between(grid,0,signal,color=COLORS[0],alpha=.35);ax.plot(grid,signal,c=COLORS[0],lw=1)
            ax.set(xlim=(0,100),ylim=(-.1,2.6),yticks=[.35,1.82],yticklabels=['Signal','Intervals'],xlabel='Position')
        else:raise ValueError(kind)
        fig.suptitle(title or dict((k,n) for k,n,_ in CATALOG)[kind],fontsize=12,y=.965,fontfamily='Microsoft YaHei')
        fig._fam_template_data=data;fig._fam_template_edition='single-v3';fig._fam_paper_kind=kind;fig._fam_chart_type=kind
        for ax in fig.axes:
            for line in ax.lines:
                if kind not in ('paired',):line._fam_fit_exclude=True
        return fig

def apply_variants(fig,p):
    kind=getattr(fig,'_fam_graphkind',None);data=getattr(fig,'_fam_template_data',{});ax=fig.axes[0]
    if kind in ('raincloud','paired','estimation') and 'showObservations' in p:
        from matplotlib.collections import PathCollection
        for collection in ax.collections:
            if isinstance(collection,PathCollection):collection.set_visible(p['showObservations'])
    if kind=='paired' and 'showPairLines' in p:
        for line in ax.lines:line.set_visible(p['showPairLines'])
    if kind=='raincloud' and 'showDistribution' in p:
        from matplotlib.collections import FillBetweenPolyCollection
        for collection in ax.collections:
            if isinstance(collection,FillBetweenPolyCollection):collection.set_visible(p['showDistribution'])
    if kind=='hexbin' and 'hexGridSize' in p:
        original=ax.collections[0];identifier=original.get_gid();cbar=original.colorbar
        replacement=ax.hexbin(data['x'],data['y'],gridsize=p['hexGridSize'],mincnt=1,cmap=original.cmap,linewidths=0)
        replacement.set_gid(identifier);original.remove()
        if cbar:cbar.update_normal(replacement);replacement.colorbar=cbar
    if kind=='correlation' and 'correlationTriangle' in p:
        values=np.asarray(data['r']);mode=p['correlationTriangle'];mask=np.triu(np.ones_like(values,dtype=bool),1) if mode=='lower' else np.tril(np.ones_like(values,dtype=bool),-1) if mode=='upper' else np.zeros_like(values,dtype=bool)
        ax.images[0].set_data(np.ma.array(values,mask=mask))
        # Existing values occupy the lower triangle; remap their positions,
        # preserving text identity and source coefficients when flipping.
        for text in ax.texts:
            x,y=text.get_position();text.set_position((y,x) if mode=='upper' else (x,y));text.set_visible(p.get('showCoefficients',True))
        if mode=='full':
            for i in range(len(values)):
                for j in range(i+1,len(values)):ax.text(j,i,f'{values[i,j]:.2f}',ha='center',va='center',fontsize=9,color='white' if abs(values[i,j])>.65 else '#263238',visible=p.get('showCoefficients',True))
    elif kind=='correlation' and 'showCoefficients' in p:
        for text in ax.texts:text.set_visible(p['showCoefficients'])

def validate_variants(p):
    from adjustments import finite
    for key in ('showObservations','showPairLines','showDistribution','showCoefficients'):
        if key in p and not isinstance(p[key],bool):raise ValueError('新图型显示开关需要布尔值')
    if 'hexGridSize' in p:
        finite(p['hexGridSize'],5,150)
        if not isinstance(p['hexGridSize'],int):raise ValueError('六边形分箱数需要整数')
    if p.get('correlationTriangle','lower') not in ('lower','upper','full'):raise ValueError('相关矩阵三角显示无效')
