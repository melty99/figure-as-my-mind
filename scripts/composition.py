"""Fit panel headings into the available physical header without changing data frames."""
import copy
import re
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import RendererAgg

def title_settings(record,group,panel,index,*,_readonly=False):
    result=dict(record) if _readonly else copy.deepcopy(record)
    label=panel.get('label',chr(97+index)) if group.get('labels',True) else ''
    result.setdefault('native',{})['compositionHeader']={'label':label,'labelSize':group.get('labelSize',16),'labelFamily':group.get('labelFamily','Arial')}
    return result

def wrap(text,font,width,renderer):
    lines=[]
    for original in text.split('\n'):
        if original.count('$')>=2 and original.count('$')%2==0:
            lines.append(original);continue
        line=''
        for token in original:
            candidate=line+token
            if line and renderer.get_text_width_height_descent(candidate,font,False)[0]>width:
                # Prefer breaking at words, fall back to characters for CJK or long tokens.
                boundary=line.rfind(' ')
                if boundary>0:lines.append(line[:boundary]);line=line[boundary+1:]+token
                else:lines.append(line);line=token
            else:line=candidate
        lines.append(line)
    return '\n'.join(lines)

def apply_header(fig,config):
    text=fig._suptitle
    if text is None or not text.get_visible() or not text.get_text():return
    renderer=RendererAgg(1,1,72);width=fig.get_figwidth()*72;height=fig.get_figheight()*72
    label=config.get('label','');label_font=FontProperties(family=config.get('labelFamily','Arial'),size=config.get('labelSize',16),weight='bold')
    reserve=renderer.get_text_width_height_descent(label,label_font,False)[0]+12 if label else 0
    left=6+reserve;right=width-6;available=max(12,right-left)
    top=max((a.get_position().y1 for a in fig.axes if not hasattr(a,'_colorbar')),default=.85)
    room=max(12,(1-top)*height-10);original=text.get_text();requested=text.get_fontsize();font=text.get_fontproperties().copy()
    for size in [requested]+list(range(int(requested)-1,6,-1)):
        font.set_size(size);wrapped=wrap(original,font,available,renderer);lines=wrapped.count('\n')+1
        measured=max((renderer.get_text_width_height_descent(line,font,bool(re.search(r'\$.*\$',line)))[0] for line in wrapped.split('\n')),default=0)
        if lines*size*1.25<=room and measured<=available:break
    text.set_text(wrapped);text.set_fontsize(size);text.set_position(((left+right)/2/width,1-6/height));text.set_ha('center');text.set_va('top');text._autopos=False

