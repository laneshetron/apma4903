"""Reproduce the three index.html charts as vector plots and self-contained TeX."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/prediction-mm-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

ROOT=Path(__file__).resolve().parents[1]
COLORS={'orig':'#7C3AED','aware':'#059669','p':'#16181D','hazard':'#F59E0B','event':'#DC2626'}

def main():
    data=json.loads((ROOT/'results/prototype_path.json').read_text())
    s=data['simulation']; c=data['grid']; params=data['params']; n=c['N']
    pre=np.arange(n)/n; post=np.arange(1,n+1)/n; all_t=np.arange(n+1)/n
    event=None if s['eventIndex'] is None else (s['eventIndex']+1)/n
    h=np.asarray(s['hazard']); q0=params['q0']
    plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','axes.spines.top':False,
                         'axes.spines.right':False,'legend.frameon':False,'pdf.fonttype':42})
    fig=plt.figure(figsize=(10,7.2),layout='constrained'); gs=GridSpec(2,2,figure=fig,height_ratios=[1.25,1])
    price=fig.add_subplot(gs[0,:]); inventory=fig.add_subplot(gs[1,0]); pnl=fig.add_subplot(gs[1,1])
    for i in range(n):
        price.axvspan(i/n,(i+1)/n,color=COLORS['hazard'],alpha=.04+.26*h[i]/max(h),lw=0)
    price.plot(all_t,s['p'],color=COLORS['p'],lw=2,label='Fair probability')
    for name,label in [('orig','Diffusion benchmark'),('aware','Event-aware')]:
        price.step(all_t,s[name]['bid']+[s[name]['bid'][-1]],where='post',color=COLORS[name],lw=1.4,label=label+' bid')
        price.step(all_t,s[name]['ask']+[s[name]['ask'][-1]],where='post',color=COLORS[name],lw=1.4,ls='--',label=label+' ask')
        inventory.step(all_t,[q0]+s[name]['q'],where='post',color=COLORS[name],lw=1.8,label=label)
        pnl.plot(all_t,[0]+s[name]['pnl'],color=COLORS[name],lw=1.8,label=label)
    price.set(title='A  Fair probability, quotes, and anticipated information',ylabel='Probability / quote ($)',ylim=(0,1))
    price.legend(ncol=3,fontsize=8,loc='upper left')
    inventory.set(title='B  Inventory',ylabel='Inventory (contracts)')
    pnl.set(title='C  Marked-to-market P&L',ylabel='P&L relative to initial wealth ($)')
    inventory.legend(fontsize=8); pnl.legend(fontsize=8)
    for ax in [price,inventory,pnl]:
        ax.set_xlim(0,1); ax.set_xlabel('Time / horizon')
        ax.grid(axis='y',color='#E7E9EF',lw=.7); ax.set_axisbelow(True)
        if event is not None: ax.axvline(event,color=COLORS['event'],ls='--',lw=1.2)
    fig.savefig(ROOT/'figures/prototype_three_charts.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'figures/prototype_three_charts.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
    def coords(x,y):
        return ' '.join(f'({xx:.8f},{yy:.8f})' for xx,yy in zip(x,y))
    def line(x,y,style):
        return r'\addplot['+style+'] coordinates {'+coords(x,y)+'};\n'
    def eventline(ymin,ymax):
        if event is None: return ''
        return line([event,event],[ymin,ymax],'prototypeevent,dashed,thick,forget plot')
    # Same source series, with pre- and post-step values placed at their physical times.
    # Last pre-step quote is held through t=1 so its last holding interval is visible.
    plot=r'''{\footnotesize
\textcolor{prototypeoriginal}{\rule{12pt}{1pt}} Diffusion benchmark\quad
\textcolor{prototypeaware}{\rule{12pt}{1pt}} Event-aware\quad
\textcolor{black}{\rule{12pt}{1pt}} Fair probability\par
Solid bid; dashed ask. Orange: conditional event probability. Red: realized event.}
\par\medskip
\begin{tikzpicture}
\begin{axis}[width=0.96\linewidth,height=0.36\linewidth,
xmin=0,xmax=1,ymin=0,ymax=1,axis lines=left,ymajorgrids,grid style={gray!20},
label style={font=\scriptsize},tick label style={font=\scriptsize},
title style={font=\small},title={A: Probability and quotes},
xlabel={Time / horizon},ylabel={Probability / quote (\$)}]
'''
    for i in range(n):
        opacity=.04+.26*h[i]/max(h)
        plot+=r'\addplot[draw=none,fill=prototypehazard,fill opacity='+f'{opacity:.6f}'+r',forget plot] coordinates {'+coords([i/n,(i+1)/n,(i+1)/n,i/n],[0,0,1,1])+r'} \closedcycle;'+'\n'
    for name,color in [('orig','prototypeoriginal'),('aware','prototypeaware')]:
        plot+=line(all_t,s[name]['bid']+[s[name]['bid'][-1]],color+',const plot,thick')
        plot+=line(all_t,s[name]['ask']+[s[name]['ask'][-1]],color+',const plot,thick,dashed')
    plot+=line(all_t,s['p'],'black,very thick')+eventline(0,1)
    plot+=r'''\end{axis}\end{tikzpicture}
\par\bigskip
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.3cm},
width=0.445\linewidth,height=0.32\linewidth,
xmin=0,xmax=1,axis lines=left,ymajorgrids,grid style={gray!20},
label style={font=\scriptsize},tick label style={font=\scriptsize},
title style={font=\small}]
\nextgroupplot[title={B: Inventory},xlabel={Time / horizon},ylabel={Inventory (contracts)}]
'''
    qvals=[q0]+s['orig']['q']+s['aware']['q']; qlow=min(qvals)-1; qhigh=max(qvals)+1
    for name,color in [('orig','prototypeoriginal'),('aware','prototypeaware')]:
        plot+=line(all_t,[q0]+s[name]['q'],color+',const plot,thick')
    plot+=eventline(qlow,qhigh)
    plot+=r'''\nextgroupplot[title={C: Marked-to-market P\&L},xlabel={Time / horizon},ylabel={Marked P\&L (\$)}]
'''
    wealth=[0]+s['orig']['pnl']+s['aware']['pnl']; low=min(wealth); high=max(wealth)
    pad=.08*(high-low)
    for name,color in [('orig','prototypeoriginal'),('aware','prototypeaware')]:
        plot+=line(all_t,[0]+s[name]['pnl'],color+',thick')
    plot+=eventline(low-pad,high+pad)
    plot+=r'\end{groupplot}\end{tikzpicture}'
    eventtext='not realized' if event is None else f'$t={event:.5f}$'
    text=r'''\clearpage
\subsection{Illustrative path from the interactive prototype}
\label{sec:prototype}
To connect the aggregate experiment to individual trading decisions,
Figure~\ref{fig:prototype} reproduces the three charts in the supplied
\texttt{index.html}: probability and quotes, inventory, and marked-to-market
P\&L. We execute the page's original computational functions with its default
inputs and random seed 2718; we do not select a favorable path from repeated
runs. Initial inventory is $q_0=3$, financed by $X_0=-3(0.5)$, so initial marked
wealth is zero. The timing-distribution center is $0.65$, its width is $0.075$,
$\rho_s=0.50$, $\lambda_u=0.30$, and $\rho_u=0.25$.

This prototype has 64 time intervals, 25 probability nodes on $[0.05,0.95]$,
17 inventory states on $[-8,8]$, and quote offsets
$\{0.015,0.030,0.055,0.090,0.140\}$. Its remaining constants are
$\bar\sigma=0.82$, $\gamma=0.04$, $\gamma_T=0.01$, $A=22$, and $k=34$.
It constructs a discrete Gaussian event-time mass with total probability
$0.997$ and converts that mass into conditional per-step arrival probabilities.
The orange background in Panel A encodes these conditional probabilities,
which are distinct from the Gaussian-shaped continuous hazard in the main
Monte Carlo experiment.

The displayed path's anticipated event is '''+eventtext+r'''. Final marked
P\&L is '''+f"\\${s['orig']['pnl'][-1]:.4f} for the diffusion benchmark and\n\\${s['aware']['pnl'][-1]:.4f} for the event-aware prototype. Their cumulative\nstale-execution losses are \\${s['makers']['orig']['pickoff']:.4f} and\n\\${s['makers']['aware']['pickoff']:.4f}, respectively.\n"+r'''
These are outcomes of one seeded path, not estimates of expected performance.

\begin{figure}[p]
\centering
'''+plot+r'''
\caption{Reproduction of the three interactive-prototype charts at default
settings and seed 2718. The upper panel shows fair probability and both
policies' bids and asks; the lower panels show inventory and marked P\&L.
Quotes are plotted at the start of each holding interval; inventory and P\&L
are plotted after each transition, with their initial values included. The
vertical red line marks the realized anticipated event. These physical-time
conventions replace the web page's common index-based horizontal scale.
The full terminal probability is included; the interactive plot truncates its
last probability observation. Colors reproduce the prototype's light theme.}
\label{fig:prototype}
\end{figure}

This illustration preserves the prototype's numerical behavior. It is a
separate configuration from the validated Monte Carlo comparison above. In
particular, the prototype clips probabilities to $[0.05,0.95]$, uses nearest-node
continuation values, and has different ordinary-fill approximations in its
Bellman recursion and its simulator. Its figures should therefore be read as
an illustration of that supplied implementation. They do not extend the main
experiment's Bellman-value validation or grid-refinement conclusions.
Exact replay data, default settings, and source hashes are saved in
\path{results/prototype_path.json}; reproduction scripts are
\path{simulation/reproduce_prototype.mjs} and
\path{simulation/prototype_report.py}.
'''
    (ROOT/'results/prototype_section.tex').write_text(text)
    source=ROOT/'event_aware_market_making.tex'; tex=source.read_text()
    definitions=r'''\definecolor{prototypeoriginal}{HTML}{7C3AED}
\definecolor{prototypeaware}{HTML}{059669}
\definecolor{prototypehazard}{HTML}{F59E0B}
\definecolor{prototypeevent}{HTML}{DC2626}
'''
    if r'\definecolor{prototypeoriginal}' not in tex:
        tex=tex.replace(r'\newcommand{\E}',definitions+r'\newcommand{\E}',1)
    start='% BEGIN GENERATED PROTOTYPE CHARTS'; end='% END GENERATED PROTOTYPE CHARTS'
    block=start+'\n'+text+'\n'+end+'\n'
    if start in tex:
        before,rest=tex.split(start,1); _,after=rest.split(end,1)
        tex=before+block+after.lstrip('\n')
    else:
        tex=tex.replace(r'\appendix',block+'\n'+r'\clearpage'+'\n'+r'\appendix',1)
    source.write_text(tex)
    print('Generated three prototype charts and embedded them in the paper.')

if __name__=='__main__': main()
