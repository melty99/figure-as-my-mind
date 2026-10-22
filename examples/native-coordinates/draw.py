"""Synthetic software example using Matplotlib plus an explicit native scene."""
from pathlib import Path
import sys,csv,json
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parents[1]/'scripts'))
try:
    import bootstrap
except ImportError:
    pass
import matplotlib.pyplot as plt
rows=list(csv.DictReader((ROOT/'observations.csv').open(encoding='utf-8')))
x=[float(r['x']) for r in rows];y=[float(r['y']) for r in rows];se=[float(r['se']) for r in rows]
fig,ax=plt.subplots();ax.errorbar(x,y,yerr=se,fmt='o',color='#4477aa',ecolor='#222222',label='Observed');ax.set(xlabel='Time',ylabel='Response',title='Python source result');ax.legend();fig.savefig(ROOT/'python-original.svg');plt.close(fig)
layer={'kind':'errorbar','x':x,'y':y,'sourceIds':[r['id'] for r in rows],'rows':rows,'label':'Observed','errors':{'y':{'minus':se,'plus':se}},'style':{'color':'#4477aa','errorColor':'#222222','marker':'o'}}
scene={'version':1,'kind':'fam-native','panels':[{'id':'points','title':'Python source result','x':{'label':'Time'},'y':{'label':'Response'},'layers':[layer]}]}
(ROOT/'python.scene.json').write_text(json.dumps(scene,allow_nan=False),encoding='utf-8')
(ROOT/'python-import.json').write_text(json.dumps({'version':1,'language':'python','source':'draw.py','inputs':['observations.csv'],'figures':[{'scene':'python.scene.json','svg':'python-original.svg','name':'Python native coordinates'}]}),encoding='utf-8')
