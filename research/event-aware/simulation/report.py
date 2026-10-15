"""Generate the reproducible figure and LaTeX results from saved MC output."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/prediction-mm-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT=Path(__file__).resolve().parents[1]

def main():
    data=json.loads((ROOT/'results/main.json').read_text())
    half=json.loads((ROOT/'results/partial_pickoff.json').read_text())
    refinement=json.loads((ROOT/'results/refinement.json').read_text())
    samples=np.load(ROOT/'results/main_samples.npz')
    policy=np.load(ROOT/'results/policy_slices.npz')
    colors={'fn':'#B65A34','ea':'#187B80'}
    labels={'fn':'Diffusion benchmark','ea':'Event-aware'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
        'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#293746',
        'text.color':'#172A3A','axes.titleweight':'bold','axes.titlesize':11,
        'legend.frameon':False,'figure.facecolor':'white','axes.facecolor':'white',
        'pdf.fonttype':42})
    fig,axes=plt.subplots(2,2,figsize=(10,7.2),layout='constrained')
    ax=axes[0,0]
    ax.plot(policy['t'],policy['fn_spread'],color=colors['fn'],label=labels['fn'],lw=2)
    ax.plot(policy['t'],policy['ea_pending'],color=colors['ea'],label='Event-aware: pending',lw=2)
    ax.plot(policy['t'],policy['ea_completed'],color=colors['ea'],label='Event-aware: completed',lw=1.5,ls='--')
    ax.axvspan(.51,.79,color='#A8B2BA',alpha=.16,zorder=0)
    ax.set(title='A  Optimal spread at p = 0.5, q = 0',xlabel='Time / horizon',ylabel='Ask minus bid ($)')
    ax.legend(fontsize=8,loc='center right'); ax.set_xlim(0,1)
    ax=axes[0,1]; t=np.array(data['trace']['t']); q=np.array(data['trace']['q_abs'])
    for j,name in enumerate(['fn','ea']):
        ax.plot(t,q[:,j],color=colors[name],label=labels[name],lw=2)
    ax.axvspan(.51,.79,color='#A8B2BA',alpha=.16,zorder=0)
    ax.set(title='B  Inventory across shared market paths',xlabel='Time / horizon',ylabel='Mean absolute inventory (contracts)')
    ax.legend(fontsize=8); ax.set_xlim(0,1)
    ax=axes[1,0]; losses=np.array(data['trace']['stale'])
    for j,name in enumerate(['fn','ea']):
        ax.plot(t,losses[:,j],color=colors[name],label=labels[name],lw=2)
    ax.axvspan(.51,.79,color='#A8B2BA',alpha=.16,zorder=0)
    ax.set(title='C  Accumulated stale-execution losses',xlabel='Time / horizon',ylabel='Mean loss per path ($)')
    ax.legend(fontsize=8); ax.set_xlim(0,1)
    ax=axes[1,1]
    for name in ['fn','ea']:
        a=np.sort(samples[name+'_settled_wealth']); y=np.arange(1,len(a)+1)/len(a)
        ax.plot(a,y,color=colors[name],label=labels[name],lw=1.8)
    ax.axvline(0,color='#6E7F8D',lw=.8,ls=':')
    ax.set(title='D  Wealth after binary settlement',xlabel='Terminal wealth ($)',ylabel='Cumulative probability')
    ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.legend(fontsize=8,loc='lower right')
    ax.set_xlim(-2,2.5)
    for ax in axes.flat:
        ax.grid(axis='y',color='#DBE1E5',alpha=.65,lw=.7); ax.set_axisbelow(True)
    fig.savefig(ROOT/'figures/monte_carlo_comparison.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'figures/monte_carlo_comparison.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
    def coords(x,y):
        return ' '.join(f'({xx:.5f},{yy:.5f})' for xx,yy in zip(x,y))
    def line(x,y,color,extra=''):
        return r'\addplot[thick,'+color+extra+'] coordinates {'+coords(x,y)+'};\n'
    shaded=r'\addplot[draw=none,fill=gray!12,forget plot] coordinates {(0.51,0) (0.79,0) (0.79,2) (0.51,2)} \closedcycle;'
    plot=r'''{\footnotesize\textcolor{benchmark}{\rule{12pt}{1pt}} Diffusion benchmark\quad
\textcolor{eventaware}{\rule{12pt}{1pt}} Event-aware\quad
Panel A: solid pending; dashed completed}\par\medskip
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 2,horizontal sep=1.25cm,vertical sep=1.85cm},
width=0.445\linewidth,height=0.34\linewidth,
label style={font=\scriptsize},tick label style={font=\scriptsize},
title style={font=\small},legend style={font=\tiny,draw=none,fill=none},
axis lines=left,ymajorgrids,grid style={gray!20},xmin=0,xmax=1,
cycle list name=color list]
\nextgroupplot[title={A: Spread at $p=0.5$, $q=0$},xlabel={Time / horizon},
ylabel={Ask minus bid (\$)},ymin=0.09,ymax=0.53,legend pos=outer north east]
'''+shaded+'\n'
    ts=np.unique(np.linspace(0,len(policy['t'])-1,400,dtype=int))
    plot+=line(policy['t'][ts],policy['fn_spread'][ts],'benchmark')+'\n'
    plot+=line(policy['t'][ts],policy['ea_pending'][ts],'eventaware')+'\n'
    plot+=line(policy['t'][ts],policy['ea_completed'][ts],'eventaware',',dashed')+'\n'
    plot+=r'''\nextgroupplot[title={B: Inventory},xlabel={Time / horizon},
ylabel={Mean absolute inventory},ymin=0,ymax=1.6]
'''+shaded+'\n'
    for j,name in enumerate(['fn','ea']):
        plot+=line(t,q[:,j],'benchmark' if j==0 else 'eventaware')
    plot+=r'''\nextgroupplot[title={C: Stale-execution losses},xlabel={Time / horizon},
ylabel={Mean accumulated loss (\$)},ymin=0,ymax=0.185,
yticklabel style={/pgf/number format/fixed,/pgf/number format/precision=2}]
'''+shaded+'\n'
    for j,name in enumerate(['fn','ea']):
        plot+=line(t,losses[:,j],'benchmark' if j==0 else 'eventaware')
    plot+=r'''\nextgroupplot[title={D: Settled-wealth CDF},xlabel={Terminal wealth (\$)},
ylabel={Cumulative probability},xmin=-2,xmax=2.5,ymin=0,ymax=1]
'''
    for j,name in enumerate(['fn','ea']):
        values=np.sort(samples[name+'_settled_wealth'])
        idx=np.unique(np.linspace(0,len(values)-1,500,dtype=int))
        plot+=line(values[idx],(idx+1)/len(values),'benchmark' if j==0 else 'eventaware')
    plot+=r'\end{groupplot}\end{tikzpicture}'
    # Legend is placed inside A to keep the complete figure within text width.
    plot=plot.replace('legend pos=outer north east','legend pos=south east')
    a=data['controllers']['fn']; b=data['controllers']['ea']; diff=data['paired_differences']
    def fmt(m): return f"{m['mean']:.4f}"
    def interval(m): return f"[{m['low']:.4f}, {m['high']:.4f}]"
    rows=[]
    metrics=[('Marked terminal wealth ($)', 'marked_wealth'),
             ('Settled terminal wealth ($)','settled_wealth'),
             ('Penalized objective ($)','objective'),
             ('Ordinary spread revenue ($)','ordinary_spread_income'),
             ('Stale-execution loss ($)','stale_loss'),
             ('Running risk penalty ($)','risk_penalty'),
             ('Terminal risk penalty ($)','terminal_penalty'),
             ('Ordinary fills','ordinary_fills'),('Stale fills','stale_fills'),
             ('Integrated squared inventory','inventory_exposure'),
             ('Absolute inventory before event','event_abs_inventory')]
    for label,k in metrics:
        rows.append(label.replace('$',r'\$')+' & '+fmt(a[k])+' & '+fmt(b[k])+r' \\')
    rows+=['Settled wealth: 5th percentile (\\$) & '+f"{a['settled_wealth_q05']:.4f} & {b['settled_wealth_q05']:.4f}"+r' \\',
           'Settled wealth: lower-tail mean (\\$) & '+f"{a['settled_wealth_es05']:.4f} & {b['settled_wealth_es05']:.4f}"+r' \\']
    refrows=[]
    mid={'np':data['config']['np_'],'nt':data['config']['nt'],'action_step':data['config']['action_step'],
         'fn_true':data['true_environment_values']['fn'],'ea_true':data['true_environment_values']['ea']}
    mid['advantage']=mid['ea_true']-mid['fn_true']
    for r in [refinement[0],mid,refinement[1]]:
        refrows.append(f"{r['np']} & {r['nt']} & {r['action_step']:.4f} & {r['fn_true']:.5f} & {r['ea_true']:.5f} & {r['advantage']:.5f}"+r' \\')
    gain=diff['objective']; reduction=100*(1-b['stale_loss']['mean']/a['stale_loss']['mean'])
    halfgain=half['paired_differences']['objective']
    text=r'''\section{Monte Carlo comparison}
\label{sec:mc}
\subsection{Design and numerical solution}
We compare two optimized policies in a synthetic market: a constrained
Feil--Nendel diffusion benchmark and the event-aware controller. This is a
comparison of specified control models, not a replication of the empirical
calibration or numerical results of~\cite{feilnendel2026}. Both controllers use
identical quote constraints, inventory limits, ordinary-flow parameters, and
risk aversion. The benchmark optimizes a diffusion-only Bellman equation with
running charge $\gamma q^2\sigma^2$ and the same terminal penalty; the event-aware
controller optimizes both news types, stale execution, and the full variance
charge. When evaluated, both face the same actual news and pickoff mechanisms.
Thus the experiment measures the combined benefit of incorporating those
mechanisms; it does not isolate timing information alone.

The horizon is $T=1$, initial cash and inventory are zero, and $p_0=0.5$.
Trade size is $\Delta=1$; inventories range from $-5$ to $5$. The displacement
cap is $D=0.30$, and quotes straddle fair value. Ordinary-flow parameters are
$A=12$ and $k=20$, with $\sigma(t,p)=0.60p(1-p)$, $\gamma=0.30$, and
$\gamma_T=0.02$. Unscheduled news has $\lambda_u=0.30$ and $\rho_u=0.15$;
the anticipated event has $\rho_s=0.50$ and hazard
\begin{equation}
 h(t)=C\exp\!\left[-\frac12\left(\frac{t-0.65}{0.07}\right)^2\right],
 \qquad \int_0^1 h(t)\,\dd t=\log 10.
\end{equation}
The event therefore occurs with probability $0.90$ in continuous time. The
Gaussian shape describes the \emph{hazard}, not the event-time density; the
latter also contains a survival factor. These parameters are illustrative and
were fixed before inspecting the comparison's simulation results.

We solve a monotone Markov-chain approximation by backward Bellman recursion,
using 81 probability nodes and 4,000 time intervals. The candidate quote-distance
spacing is $0.005$, augmented by exact crossing thresholds for both news kernels
and by price/displacement boundaries. Inventory boundary sides are disabled
for ordinary and stale execution alike. Quote optimization separates by side
because a single news jump cannot cross both quotes. All reported controls are
numerically optimized over this finite action set.

Diffusion uses nearest-neighbor jumps with total rate
$\sigma^2/(\Delta p)^2$. News first moves to a two-point-kernel destination;
positive linear interpolation is implemented in simulation as mean-preserving
random rounding onto adjacent probability nodes. Crossing is tested at the
unrounded destination, before repricing. The Euler transition probabilities
allow at most one ordinary, diffusion, or information event per time step;
the maximum total transition probability is below one. Both solvers and the
simulator use this same discretization. The running penalty uses the original
model variance rate, rather than the small extra variance from news rounding.
Grid refinement below assesses this approximation.

The main comparison uses 30,000 independent market paths with seed 20261014.
Each pair of policies shares the exogenous path, event pickoff draws, terminal
Bernoulli draw $Y\sim\mathrm{Bernoulli}(p_T)$, and uniforms for ordinary fills;
fill decisions still depend on each policy's own quotes and inventory.
We distinguish marked wealth $X_T+Q_Tp_T$ from settled wealth $X_T+Q_TY$.
The sampled objective uses marked wealth to integrate out settlement noise,
then subtracts the full true-environment running and terminal penalties for
both policies. Confidence intervals below are paired normal intervals for mean
differences, with standard errors computed across independent paths.

\subsection{Measured performance}
\begin{table}[htbp]
\centering\small
\begin{tabular}{lrr}
\toprule
Metric (mean unless stated) & Diffusion benchmark & Event-aware\\
\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule
\end{tabular}
\caption{Synthetic-market results over 30,000 paired paths. Positive stale loss
is a cost. The lower-tail mean averages the worst 5\% of settled wealth outcomes;
quantiles and tail means are descriptive estimates without confidence intervals.}
\label{tab:mc}
\end{table}

'''+f"The event-aware controller improves the mean penalized objective by \\${gain['mean']:.4f},\nwith a paired 95\\% confidence interval {interval(gain)}. The mean marked-wealth\ndifference is \\${diff['marked_wealth']['mean']:.4f} (95\\% interval\n{interval(diff['marked_wealth'])}); the mean settled-wealth difference is\n\\${diff['settled_wealth']['mean']:.4f} (95\\% interval {interval(diff['settled_wealth'])}).\nMean stale-execution losses fall by {reduction:.1f}\\%.\n"+r'''
At $p=0.5$ and $q=0$, the event-aware policy expands the spread to $0.50$
near the hazard bump, placing quotes at $0.25$ and $0.75$. Those quotes exactly
match the anticipated two-point jump destinations, so strict crossing does not
trigger a scheduled stale fill in this state. This explains the plateau in
Panel A and the tradeoff between lower ordinary revenue and lower pickoff
losses. Abrupt quote changes reflect the atomic news kernel and the crossing
rule; they should not be interpreted as a generic smooth response to news.

These differences are conditional on this parameterization and market model.
They are not evidence of superior performance in observed prediction markets.
The correctly specified controller's objective advantage is expected in the
ideal optimization problem; its numerical magnitude, revenue tradeoff, and
out-of-objective distributional effects are the substantive measurements.

\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/monte_carlo_comparison.pdf}
\caption{Optimized policies and Monte Carlo outcomes. Panel A holds probability
and inventory fixed and distinguishes pending and completed event regimes;
it is a policy slice, not a realized quote path. Panels B--C are unconditional
sample means across shared market paths. Gray shading marks $0.65\pm2(0.07)$,
a reference region of the hazard bump, not a confidence interval or an
assertion that every event occurs there. Panel D shows empirical settled-wealth
CDFs, with the horizontal range restricted for readability.}
\label{fig:mc}
\end{figure}

\subsection{Validation, sensitivity, and limitations}
'''+f"The anticipated-event frequency is {data['event_frequency']:.4f}, compared with the\ndiscrete-model target {data['event_frequency_target']:.4f}; no path has more than one\nanticipated event. Mean unscheduled-event count is {data['mean_unscheduled_count']:.4f},\nagainst target $0.30$. Mean terminal probability is\n{data['mean_terminal_probability']['mean']:.4f} (95\\% interval\n{interval(data['mean_terminal_probability'])}), consistent with the initial martingale value.\n"+r'''
Kernel means and variances, event cash/inventory accounting, and equality of
both policies when news is removed are checked programmatically. We also
value each stored policy directly in the true discrete environment, independently
of Monte Carlo sampling. The resulting expected objectives are
'''+f"{data['true_environment_values']['fn']:.5f} for the benchmark and\n{data['true_environment_values']['ea']:.5f} for the event-aware controller.\nThe corresponding Monte Carlo discrepancies are\n{data['bellman_mc_checks']['fn']['z_score']:.2f} and\n{data['bellman_mc_checks']['ea']['z_score']:.2f} standard errors.\n"+r'''

\begin{table}[htbp]
\centering\small
\begin{tabular}{rrrrrr}
\toprule
$p$ nodes & Time steps & Action spacing & Benchmark $J$ & Event-aware $J$ & Difference\\
\midrule
'''+ '\n'.join(refrows)+r'''
\bottomrule
\end{tabular}
\caption{Direct policy valuations in each grid's true environment. All three
resolutions retain the same inventory bound. The objective advantage changes
by about 1.1\% from the middle to the finest grid. These are discretization checks,
not Monte Carlo estimates or a proof of continuous-model convergence.}
\label{tab:refinement}
\end{table}

A second 30,000-path experiment uses seed 20261015, pickoff probability
$\chi=0.5$, and a reoptimized event-aware policy. The diffusion policy is
unchanged. Its paired objective improvement is
'''+f"\\${halfgain['mean']:.4f}, with 95\\% interval {interval(halfgain)}.\n"+r'''
This checks sensitivity to certain pickoff, but leaves latency, informed
arrival times, and time-varying ordinary flow unmodeled. Inventory limits,
quote constraints, and jump sizes also merit sensitivity studies. The
matched-variance and constant-hazard controllers proposed above are not part
of this two-controller experiment, so these results cannot identify the pure
value of knowing event time. Timing misspecification remains a further test.

The scripts \texttt{simulation/monte\_carlo.py} and
\texttt{simulation/report.py} reproduce the numerical study, tables, and figure.
Machine-readable summaries, path-level outcomes, seeds, and grid diagnostics
are retained under \texttt{results/}. All monetary amounts are dollars per
unit-payoff contract; no annualization or empirical calibration is implied.
'''
    text=text.replace(r'\includegraphics[width=\linewidth]{figures/monte_carlo_comparison.pdf}',plot)
    text=text.replace('30,000',f"{data['paths']:,}")
    (ROOT/'results/monte_carlo_section.tex').write_text(text)
    source=ROOT/'event_aware_market_making.tex'
    tex=source.read_text()
    start='% BEGIN GENERATED MONTE CARLO RESULTS'
    end='% END GENERATED MONTE CARLO RESULTS'
    block=start+'\n'+text+'\n'+end+'\n'
    if start in tex:
        prefix,rest=tex.split(start,1)
        _,suffix=rest.split(end,1)
        tex=prefix+block+suffix.lstrip('\n')
    else:
        tex=tex.replace(r'\appendix',block+'\n'+r'\appendix')
    source.write_text(tex)
    print('Generated figure and results section.')

if __name__=='__main__': main()
