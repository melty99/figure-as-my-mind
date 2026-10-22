"""Editable basic plot types adapted from traced paper panels.

Only forest uses published aggregate values. Other templates have new, explicit
demonstration inputs; calculations are reproducible and sources remain separate.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from paper_templates import PAPERS as EXISTING_PAPERS

CATALOG_DATA=json.loads(Path(__file__).with_name('basic_paper_catalog.json').read_text(encoding='utf-8'))
DETAILS={t['kind']:t for t in CATALOG_DATA['templates']}
PAPERS={**EXISTING_PAPERS,**CATALOG_DATA['papers']}
CATALOG=[(t['kind'],t['name'],t['description']) for t in DETAILS.values()]
SEED=20261009
COLORS=['#0072b2','#d55e00','#009e73','#cc79a7','#e69f00','#56b4e9']

def provenance(kind):
    t=DETAILS[kind];p=PAPERS[t['paper']]
    return {'kind':t['dataMode'],'seed':None if t['dataMode']=='published-summary' else SEED,'template':kind,'templateEdition':'paper-v1',
            'paperReference':{k:p[k] for k in ('title','journal','year','doi','url')}|{'figure':t['figure']},
            'adaptation':t['adaptation'],
            'dataStatement':'Published aggregate point estimates and reported intervals, transcribed from the paper.' if t['dataMode']=='published-summary' else 'Synthetic demonstration inputs; paper layout adapted, original observations not recovered.'}

def frame(size=(6.6,4.8),projection=None):
    f=plt.figure(figsize=size);ax=f.add_subplot(111,projection=projection)
    f.subplots_adjust(left=.16,right=.94,bottom=.21,top=.85)
    return f,ax

def build(kind,title=None):
    if kind not in DETAILS:raise ValueError('未知图型模板')
    with plt.rc_context({'font.family':['Arial','Microsoft YaHei'],'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.linewidth':.8,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'svg.fonttype':'none'}):
        f,data,note=BUILDERS[kind](np.random.default_rng(SEED));t=DETAILS[kind]
        f.suptitle(title or t['name'],fontsize=13,fontfamily='Microsoft YaHei',y=.96)
        f.text(.02,.032,'PUBLISHED SUMMARY' if t['dataMode']=='published-summary' else 'SYNTHETIC DEMONSTRATION',fontsize=7,color='#536471')
        f.text(.02,.009,note,fontsize=6.8,color='#536471')
        f._fam_template_data=data;f._fam_template_edition='paper-v1';f._fam_paper_kind=kind
        return f

def bar(rng):
    f,ax=frame();categories=[f'C{i+1}' for i in range(6)];x=np.arange(6);data=[]
    for j,group in enumerate(('Group A','Group B')):
        samples=rng.normal(np.array([3.2,4.8,4.1,6.3,5.6,7.2])*(1-.21*j),.48,(8,6));mean=samples.mean(0);sd=samples.std(0,ddof=1);pos=x+(-.19 if j==0 else .19)
        bars=ax.bar(pos,mean,width=.35,color=COLORS[j],edgecolor='white',linewidth=.6,yerr=sd,capsize=3,error_kw={'ecolor':'#30343b','elinewidth':1},label=group)
        for i in range(6):
            dots=ax.scatter(pos[i]+np.linspace(-.075,.075,8),samples[:,i],s=10,facecolors='white',edgecolors=COLORS[j],linewidths=.55,zorder=3)
            dots._fam_parent_bar=bars.patches[i]
            data.extend({'category':categories[i],'group':group,'replicate':k+1,'value':float(v)} for k,v in enumerate(samples[:,i]))
    ax.set_xticks(x,categories);ax.set(xlabel='Category',ylabel='Response',ylim=(0,8.5));ax.legend(frameon=False,ncols=2,loc='upper left')
    return f,data,'Bars = mean; error bars = sample SD; dots = 8 demo replicates per category.'

def pie(rng):
    f,ax=frame(size=(6.4,4.8));values=[34,29,23,14];labels=[f'Class {c}' for c in 'ABCD']
    wedges,_,_=ax.pie(values,colors=COLORS,autopct='%1.0f%%',pctdistance=.8,startangle=90,wedgeprops={'width':.42,'edgecolor':'white','linewidth':1.6},textprops={'fontsize':10})
    ax.text(0,0,'Composition',ha='center',va='center',fontsize=11);ax.legend(wedges,labels,loc='center left',bbox_to_anchor=(.94,.5),frameon=False);ax.set_aspect('equal');f.subplots_adjust(left=.04,right=.8,bottom=.16,top=.87)
    return f,[{'class':label,'count':v} for label,v in zip(labels,values)],'Demo counts normalized to percentages; pie / donut variants share the same values.'

def line(rng):
    f,ax=frame();x=np.linspace(-2.5,2.5,100);obs=np.linspace(-2.2,2.2,9);data=[]
    for j,(shift,slope) in enumerate([(-.8,1.3),(0,1.3),(.7,1.0)]):
        yy=1/(1+10**((x-shift)*slope));oy=np.clip(1/(1+10**((obs-shift)*slope))+rng.normal(0,.012,len(obs)),0,1)
        curve=ax.plot(x,yy,color=COLORS[j],lw=1.8,label=f'Series {j+1}')[0];points=ax.plot(obs,oy,'o',ms=4,mfc='white',mec=COLORS[j],ls='none')[0];points._fam_series_line=curve
        data.append({'series':f'Series {j+1}','shift':shift,'slope':slope,'x':obs.tolist(),'observations':oy.tolist(),'curveX':x.tolist(),'curveY':yy.tolist()})
    ax.axhline(.5,color='#90979f',ls='--',lw=.7);ax.set(xlabel='X (log10 scale)',ylabel='Response',ylim=(-.02,1.04));ax.legend(frameon=False,loc='upper right')
    return f,data,'Illustrative Hill curves and demo observations; no fitted drug-interaction result.'

def heatmap(rng):
    f=plt.figure(figsize=(7,5.2));grid=f.add_gridspec(2,2,width_ratios=[20,1],height_ratios=[.45,8],left=.16,right=.91,bottom=.22,top=.84,wspace=.12,hspace=.06);ax=f.add_subplot(grid[1,0]);strip=f.add_subplot(grid[0,0]);cax=f.add_subplot(grid[1,1]);values=rng.normal(0,.7,(10,15));values[:4,:5]+=1.6;values[4:7,5:10]+=1.5;values[7:,10:]+=1.4
    z=(values-values.mean(1,keepdims=True))/values.std(1,ddof=1,keepdims=True)
    from matplotlib.colors import ListedColormap
    strip.imshow(np.asarray([ListedColormap(COLORS[:3])(np.repeat(np.arange(3),5))]),aspect='auto',interpolation='nearest');strip.set_xticks([2,7,12],['Group A','Group B','Group C']);strip.xaxis.tick_top();strip.set_yticks([])
    for s in strip.spines.values():s.set_visible(False)
    im=ax.imshow(z,cmap='RdBu_r',vmin=-2.3,vmax=2.3,aspect='auto',interpolation='nearest');ax.set_xticks(range(15),[f'S{i+1:02d}' for i in range(15)],rotation=90);ax.set_yticks(range(10),[f'V{i+1:02d}' for i in range(10)]);ax.set(xlabel='Sample',ylabel='Variable');f.colorbar(im,cax=cax,label='Row z score')
    return f,{'values':values.tolist(),'zScores':z.tolist(),'groups':np.repeat(np.arange(3),5).tolist()},'Row z scores use sample SD; group ordering shown without an inferred clustering tree.'

def pca(rng):
    f,ax=frame();values=rng.normal(size=(72,6));values[24:48]+=[1.4,.8,-.5,.1,1,.4];values[48:]+=[-.8,-1.2,.6,.4,-.5,1];z=(values-values.mean(0))/values.std(0,ddof=1);u,s,v=np.linalg.svd(z,full_matrices=False);scores=u[:,:2]*s[:2];explained=s*s/np.sum(s*s)*100
    for j,marker in enumerate(('o','s','^')):
        from matplotlib.collections import LineCollection
        a=scores[j*24:(j+1)*24];center=a.mean(0);ax.add_collection(LineCollection([[center,v] for v in a],colors=COLORS[j],linewidths=.55,alpha=.2));ax.scatter(a[:,0],a[:,1],color=COLORS[j],s=27,marker=marker,alpha=.8,edgecolors='white',linewidths=.4,label=f'Group {chr(65+j)}');ax.scatter(*center,color='#656d75',marker='X',s=45,zorder=4)
    ax.axhline(0,color='#bac0c5',ls='--',lw=.7);ax.axvline(0,color='#bac0c5',ls='--',lw=.7);ax.set(xlabel=f'PC1 ({explained[0]:.1f}%)',ylabel=f'PC2 ({explained[1]:.1f}%)');ax.legend(frameon=False,loc='upper right')
    return f,{'matrix':values.tolist(),'scores':scores.tolist(),'explainedPercent':explained.tolist(),'loadings':v[:2].tolist(),'centroids':[a.mean(0).tolist() for a in np.split(scores,3)]},'PCA = standardized SVD; gray centroids and spokes computed from demo scores.'

def tree(rng):
    f,ax=frame(size=(7.2,5.2));from templates import tree_plot
    newick='(((Taxon_A:0.10,Taxon_B:0.14):0.08,Taxon_C:0.22):0.11,((Taxon_D:0.15,Taxon_E:0.18):0.12,(Taxon_F:0.12,Taxon_G:0.16):0.10):0.14,Taxon_H:0.55);';tree_plot(ax,newick)
    for i,t in enumerate(ax.texts):t.set_color(COLORS[(i//3)%3]);t.set_fontsize(9)
    ax.set_xlim(-.02,.86);scale=ax.plot([0,.1],[-.72,-.72],color='#333',lw=1.3)[0];scale._fam_independent=True;label=ax.text(.05,-.98,'0.10',ha='center',fontsize=8);label._fam_scale_label=True;ax.set_ylim(-1.25,8);ax.set_axis_off()
    return f,{'newick':newick,'inputPolicy':'Explicit example topology and branch lengths; no sequences or bootstraps.'},'Example Newick with branch-length scale; no inferred phylogeny or bootstrap support.'

def vk_data(rng):
    result=[]
    for j,(ratio,hratio) in enumerate([(.23,1.65),(.48,1.2),(.68,1.1)]):
        for i in range(75):
            c=int(rng.integers(15,36));o=max(1,int(round(c*np.clip(rng.normal(ratio,.09),.05,.95))));h=max(2,int(round(c*np.clip(rng.normal(hratio,.2),.55,2.15))))
            result.append({'formula':f'C{c}H{h}O{o}','group':f'Group {chr(65+j)}','C':c,'H':h,'O':o,'OC':o/c,'HC':h/c})
    return result

def vk(rng):
    f=plt.figure(figsize=(6.8,5.4));grid=f.add_gridspec(2,2,width_ratios=[5,1.1],height_ratios=[1.1,5],left=.14,right=.93,bottom=.2,top=.86,hspace=.05,wspace=.05);ax=f.add_subplot(grid[1,0]);top=f.add_subplot(grid[0,0],sharex=ax);right=f.add_subplot(grid[1,1],sharey=ax);data=vk_data(rng)
    for j in range(3):
        values=[v for v in data if v['group']==f'Group {chr(65+j)}'];x=np.array([v['OC'] for v in values]);y=np.array([v['HC'] for v in values]);ax.scatter(x,y,color=COLORS[j],s=14,alpha=.65,edgecolors='none',label=f'Group {chr(65+j)}');top.hist(x,bins=np.linspace(0,1,21),histtype='step',color=COLORS[j],density=True,lw=1);right.hist(y,bins=np.linspace(.4,2.4,21),histtype='step',orientation='horizontal',color=COLORS[j],density=True,lw=1)
    ax.set(xlim=(0,1),ylim=(.4,2.4),xlabel='O/C',ylabel='H/C');ax.legend(frameon=False,loc='lower left',fontsize=8);top.tick_params(labelbottom=False,bottom=False);right.tick_params(labelleft=False,left=False);top.set_yticks([]);right.set_xticks([])
    return f,data,'O/C and H/C computed from explicit demo formulae; marginal distributions use common bins.'

def scatter(rng):
    f,ax=frame();data=[]
    for j in range(2):
        x=np.linspace(.4,9.6,36);y=1.1+.56*x+j*.9+rng.normal(0,.65,len(x));design=np.column_stack([np.ones(len(x)),x]);coef=np.linalg.lstsq(design,y,rcond=None)[0];grid=np.linspace(0,10,100);pred=coef[0]+coef[1]*grid;res=y-design@coef;sd=np.sqrt(np.sum(res**2)/(len(x)-2));se=sd*np.sqrt(1/len(x)+(grid-x.mean())**2/np.sum((x-x.mean())**2))
        ax.scatter(x,y,color=COLORS[j],s=22,alpha=.8,edgecolors='white',linewidths=.4,label=f'Group {chr(65+j)}');curve=ax.plot(grid,pred,color=COLORS[j],lw=1.5)[0];band=ax.fill_between(grid,pred-1.96*se,pred+1.96*se,color=COLORS[j],alpha=.14);band._fam_curve=curve;data.append({'group':f'Group {chr(65+j)}','x':x.tolist(),'y':y.tolist(),'coefficients':coef.tolist()})
    ax.set(xlabel='Predictor',ylabel='Response');ax.legend(frameon=False)
    return f,data,'OLS lines; shaded mean intervals use a 1.96 normal approximation on demo inputs.'

def box(rng):
    f,ax=frame();values=[rng.normal(1+j*.45,.65+j*.06,48) for j in range(4)];artists=ax.boxplot(values,patch_artist=True,widths=.55,showfliers=True,medianprops={'color':'#333','linewidth':1.3},whiskerprops={'color':'#444','linewidth':.9},capprops={'color':'#444','linewidth':.9})
    for j,p in enumerate(artists['boxes']):p.set_facecolor(COLORS[j]);p.set_alpha(.7);p.set_edgecolor(COLORS[j])
    # Points belong to box fliers so native capture retains their exact box owner.
    for j,(points,raw) in enumerate(zip(artists['fliers'],values)):
        points.set_data(np.full(len(raw),j+1)+rng.uniform(-.11,.11,len(raw)),raw);points.set_visible(True);points.set_marker('o');points.set_markersize(2.7);points.set_markerfacecolor('white');points.set_markeredgecolor(COLORS[j]);points.set_markeredgewidth(.65)
    ax.set_xticks(range(1,5),['Group A','Group B','Group C','Group D']);ax.set(xlabel='Group',ylabel='Value')
    return f,{'samples':[v.tolist() for v in values]},'Box = Q1–Q3; center = median; whiskers = 1.5 IQR; all 48 demo values shown per group.'

def violin(rng):
    f,ax=frame();values=[rng.lognormal(j*.2-.2,.38,70) for j in range(4)];artists=ax.violinplot(values,showmeans=False,showmedians=True,showextrema=False,widths=.78)
    for j,p in enumerate(artists['bodies']):p.set_facecolor(COLORS[j]);p.set_edgecolor(COLORS[j]);p.set_alpha(.7)
    artists['cmedians'].set_color('#333');artists['cmedians'].set_linewidth(1.2)
    ax.boxplot(values,widths=.1,patch_artist=True,showfliers=False,boxprops={'facecolor':'white','edgecolor':'#333','linewidth':.7},medianprops={'color':'#333','linewidth':1},whiskerprops={'linewidth':.7},capprops={'linewidth':.7})
    ax.set_xticks(range(1,5),['Group A','Group B','Group C','Group D']);ax.set(xlabel='Group',ylabel='Value')
    return f,{'samples':[v.tolist() for v in values]},'Violin density from demo samples; inset white boxes show quartiles and median.'

def histogram(rng):
    f,ax=frame();samples=[rng.normal(-.3,.75,250),rng.normal(.65,.6,250)];bins=np.linspace(-3,3,25)
    for j,v in enumerate(samples):ax.hist(v,bins=bins,color=COLORS[j],alpha=.4,edgecolor='white',linewidth=.5,label=f'Group {chr(65+j)}')
    ax.set(xlabel='Value',ylabel='Count',xlim=(-3,3));ax.legend(frameon=False)
    return f,{'samples':[v.tolist() for v in samples],'binEdges':bins.tolist()},'Demo values with shared histogram bins; adapted marginal-distribution variant.'

def bubble(rng):
    f,ax=frame(size=(7.4,5.4));fraction=rng.uniform(.08,.92,(5,8));value=rng.normal(0,.85,(5,8));xx,yy=np.meshgrid(np.arange(8),np.arange(5));im=ax.scatter(xx.ravel(),yy.ravel(),s=(fraction*160).ravel(),c=value.ravel(),cmap='RdBu_r',vmin=-2,vmax=2,edgecolors='#555',linewidths=.25)
    ax.set_xticks(range(8),[f'V{i+1}' for i in range(8)]);ax.set_yticks(range(5),[f'Group {chr(65+i)}' for i in range(5)]);ax.set(xlabel='Variable',ylabel='Group',xlim=(-.5,7.5),ylim=(4.5,-.5));ax.set_axisbelow(True);ax.grid(color='#e8ebed',lw=.5);f.colorbar(im,ax=ax,label='Scaled value',pad=.035)
    handles=[ax.scatter([],[],s=p*160,facecolor='white',edgecolor='#444',linewidth=.6,label=f'{p:.0%}') for p in (.25,.5,.75)];ax.legend(handles=handles,title='Fraction',ncols=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.15));f.subplots_adjust(bottom=.29)
    return f,{'fraction':fraction.tolist(),'value':value.tolist(),'areaScale':160},'Marker area is proportional to demo fraction; color encodes an independent scaled value.'

def forest(rng):
    from paper_templates import forest as published_forest
    return published_forest(rng)

def surface3d(rng):
    f,ax=frame(projection='3d');x=np.linspace(-2,2,40);xx,yy=np.meshgrid(x,x);a=1/(1+10**(-xx));b=1/(1+10**(-yy));z=1-(1-a)*(1-b);im=ax.plot_surface(xx,yy,z,cmap='RdYlBu',vmin=0,vmax=1,linewidth=0,antialiased=True,alpha=.96)
    ax.set(xlabel='X (log10)',ylabel='Y (log10)',zlabel='Response',zlim=(0,1));ax.view_init(elev=26,azim=-135);ax.set_box_aspect((1,1,.7));f.colorbar(im,ax=ax,shrink=.58,pad=.1,label='Response');f.subplots_adjust(left=.03,right=.87,bottom=.18)
    return f,{'x':xx.tolist(),'y':yy.tolist(),'z':z.tolist(),'formula':'a=1/(1+10**(-x)); b=1/(1+10**(-y)); z=1-(1-a)*(1-b)'},'Illustrative independent-response surface; no MuSyC fit or empirical synergy estimate.'

def scatter3d(rng):
    f,ax=frame(projection='3d');data=[]
    for j in range(3):
        t=np.linspace(0,1,55);angle=2*np.pi*j/3;xyz=np.column_stack([t*np.cos(angle),t*np.sin(angle),.75*t+(.35 if j==1 else -.18 if j==2 else 0)*t*t]);cloud=xyz+rng.normal(0,.045,xyz.shape)
        ax.scatter(*cloud.T,color=COLORS[j],s=15,alpha=.75,edgecolors='none',label=f'Group {chr(65+j)}');ax.plot(*xyz.T,color=COLORS[j],lw=1.4);data.append({'group':f'Group {chr(65+j)}','xyz':cloud.tolist(),'trajectory':xyz.tolist()})
    ax.set(xlabel='Component 1',ylabel='Component 2',zlabel='Component 3');ax.view_init(elev=24,azim=-55);ax.set_box_aspect((1,1,.85));ax.legend(frameon=False,loc='upper left',fontsize=8)
    return f,data,'Synthetic XYZ point clouds and trajectories; no MLLE, pseudotime or STREAM inference.'

def contour(rng):
    f,ax=frame();x=np.linspace(-3,3,80);xx,yy=np.meshgrid(x,x);z=np.zeros_like(xx)
    for cx,cy,sx,sy,weight in [(-1.4,.9,.52,.62,1),(1.2,1,.62,.42,.8),(.3,-1.3,.76,.5,.9)]:z+=weight*np.exp(-.5*((xx-cx)**2/sx**2+(yy-cy)**2/sy**2))
    im=ax.contourf(xx,yy,z,levels=np.linspace(0,1.05,13),cmap='viridis');ax.contour(xx,yy,z,levels=np.linspace(.1,.9,5),colors='white',linewidths=.5,alpha=.6);ax.set(xlabel='X',ylabel='Y',aspect='equal');f.colorbar(im,ax=ax,label='Relative density')
    return f,{'x':xx.tolist(),'y':yy.tolist(),'density':z.tolist(),'model':'Three explicit Gaussian components'},'Analytic Gaussian-mixture demo field; no t-SNE or empirical density reconstruction.'

BUILDERS={k:globals()[k] for k in DETAILS}
