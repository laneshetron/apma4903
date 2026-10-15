"""Reproducible Bellman/Monte Carlo study of event-aware prediction-market quotes.

The benchmark is a constrained, symmetric-intensity Feil--Nendel specification,
not a replication of their published calibration. All money units are dollars
per $1 contract, and time is normalized to a horizon of one.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict, replace
import json
from pathlib import Path
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Config:
    np_: int = 81
    nt: int = 4000
    qmax: int = 5
    action_step: float = .005
    D: float = .30
    A: float = 12.
    k: float = 20.
    sigma: float = .60
    gamma: float = .30
    gamma_T: float = .02
    lambda_u: float = .30
    rho_u: float = .15
    rho_s: float = .50
    event_mass: float = 2.302585092994046  # integrated hazard => 90% arrival
    event_center: float = .65
    event_width: float = .07
    chi: float = 1.

class Grid:
    def __init__(self, c):
        self.c = c
        self.p = np.linspace(0, 1, c.np_)
        self.q = np.arange(-c.qmax, c.qmax + 1)
        self.dt = 1/c.nt
        self.t = np.arange(c.nt)*self.dt
        raw = np.exp(-.5*((self.t-c.event_center)/c.event_width)**2)
        self.h = c.event_mass*raw/(raw.sum()*self.dt)
        self.var = (c.sigma*self.p*(1-self.p))**2
        self.rate = self.var/(self.p[1]-self.p[0])**2
        self.kernels = []
        for rho in [c.rho_u, c.rho_s]:
            dest = np.array([(1-rho)*self.p, self.p+rho*(1-self.p)])
            z = dest*(c.np_-1)
            lo = np.minimum(np.floor(z).astype(int), c.np_-2)
            weight = z-lo
            prob = np.array([1-self.p, self.p])
            self.kernels.append((dest,lo,weight,prob))
        # Distance grid plus exact no-crossing thresholds and displacement cap.
        base = np.arange(0, c.D+c.action_step/2, c.action_step)
        self.db = np.minimum(np.column_stack([np.broadcast_to(base,(c.np_,len(base))),
                            c.rho_u*self.p,c.rho_s*self.p]), self.p[:,None])
        self.da = np.minimum(np.column_stack([np.broadcast_to(base,(c.np_,len(base))),
                            c.rho_u*(1-self.p),c.rho_s*(1-self.p)]),1-self.p[:,None])
        self.db = np.minimum(self.db,c.D)
        self.da = np.minimum(self.da,c.D)
        self.lb = c.A*np.exp(-c.k*self.db)
        self.la = c.A*np.exp(-c.k*self.da)
        assert self.dt*(self.rate.max()+c.lambda_u+self.h.max()+2*c.A)<1

    def interp(self, W, kind):
        _, lo, w, _ = self.kernels[kind]
        return (1-w[...,None])*W[lo]+w[...,None]*W[lo+1]

    def terms(self, V, i, event=True):
        """Euler Bellman generator, separated into independent bid/ask choices."""
        c = self.c
        # V has regime, probability, inventory dimensions.
        gen = np.zeros_like(V)
        gen[:,1:-1] = .5*self.rate[None,1:-1,None]*(V[:,2:]-2*V[:,1:-1]+V[:,:-2])
        variance = np.broadcast_to(self.var,(2,c.np_)).copy()
        buy = np.concatenate([V[:,:,1:]-V[:,:,:-1],np.zeros_like(V[:,:,:1])],axis=2)
        sell = np.concatenate([np.zeros_like(V[:,:,:1]),V[:,:,:-1]-V[:,:,1:]],axis=2)
        hb = self.lb[None,:,None,:]*(self.db[None,:,None,:]+buy[:,:,:,None])
        ha = self.la[None,:,None,:]*(self.da[None,:,None,:]+sell[:,:,:,None])
        if event:
            for s in [0,1]:
                for kind, intensity, target in [(0,c.lambda_u,s),(1,self.h[i] if s==0 else 0,1)]:
                    if intensity==0:
                        continue
                    dest,_,_,prob = self.kernels[kind]
                    w = self.interp(V[target],kind)
                    gen[s] += intensity*((prob[...,None]*w).sum(axis=0)-V[s])
                    rho = c.rho_u if kind==0 else c.rho_s
                    variance[s] += intensity*rho*rho*self.p*(1-self.p)
                    wb = np.concatenate([w[:,:,1:]-w[:,:,:-1],np.zeros_like(w[:,:,:1])],axis=2)
                    wa = np.concatenate([np.zeros_like(w[:,:,:1]),w[:,:,:-1]-w[:,:,1:]],axis=2)
                    for d in [0,1]:
                        b = self.p[:,None]-self.db
                        a = self.p[:,None]+self.da
                        ib = dest[d,:,None] < b-1e-12
                        ia = dest[d,:,None] > a+1e-12
                        hb[s] += intensity*c.chi*prob[d,:,None,None]*ib[:,None,:]*(wb[d,:,:,None]+(dest[d,:,None]-b)[:,None,:])
                        ha[s] += intensity*c.chi*prob[d,:,None,None]*ia[:,None,:]*(wa[d,:,:,None]+(a-dest[d,:,None])[:,None,:])
        # Inventory boundaries disable ALL executions on the respective side.
        hb[:,:,-1,:] = 0
        ha[:,:,0,:] = 0
        gen -= c.gamma*variance[:,:,None]*self.q[None,None,:]**2
        return gen,hb,ha

def solve(c, name):
    g = Grid(c)
    terminal = -c.gamma_T*g.p[:,None]*(1-g.p[:,None])*g.q[None,:]**2
    V = np.repeat(terminal[None],2,axis=0)
    shape=(c.nt,2,c.np_,len(g.q),2)
    actions=np.empty(shape,dtype=np.uint8)
    assert g.db.shape[-1] <=256
    started=time.time()
    for i in range(c.nt-1,-1,-1):
        gen,hb,ha=g.terms(V,i,event=name!='fn')
        ab=hb.argmax(axis=-1); aa=ha.argmax(axis=-1)
        actions[i,...,0]=ab; actions[i,...,1]=aa
        V=V+g.dt*(gen+np.take_along_axis(hb,ab[...,None],-1)[...,0]+np.take_along_axis(ha,aa[...,None],-1)[...,0])
    print(f'Solved {name}: grid {c.np_}/{c.nt}, value {V[0,c.np_//2,c.qmax]:.8f}, {time.time()-started:.1f}s',flush=True)
    return {'name':name,'actions':actions,'value':float(V[0,c.np_//2,c.qmax]),'grid':g}

def evaluate(policy, env):
    """Exact expected objective of a stored policy in the discrete true environment."""
    c=env; g=Grid(c)
    V=np.repeat((-c.gamma_T*g.p[:,None]*(1-g.p[:,None])*g.q[None,:]**2)[None],2,axis=0)
    for i in range(c.nt-1,-1,-1):
        gen,hb,ha=g.terms(V,i,event=True)
        a=policy['actions'][i]
        V += g.dt*(gen+np.take_along_axis(hb,a[...,0,None],-1)[...,0]+np.take_along_axis(ha,a[...,1,None],-1)[...,0])
    return float(V[0,c.np_//2,c.qmax])

def mean_ci(a):
    m=float(np.mean(a)); se=float(np.std(a,ddof=1)/np.sqrt(len(a)))
    return {'mean':m,'se':se,'low':m-1.96*se,'high':m+1.96*se}

def simulate(policies, env, paths=30000, seed=20261014, tag='main'):
    g=Grid(env); c=env; rng=np.random.default_rng(seed); M=len(policies)
    pidx=np.full(paths,c.np_//2,dtype=int); s=np.zeros(paths,dtype=int)
    q=np.zeros((M,paths),dtype=int); cash=np.zeros((M,paths))
    risk=np.zeros_like(cash); spread_income=np.zeros_like(cash); stale_loss=np.zeros_like(cash)
    ordinary=np.zeros_like(q); picked=np.zeros_like(q); integrated_q2=np.zeros_like(cash)
    event_q=np.full_like(cash,np.nan); event_times=np.full(paths,np.nan)
    trace={'t':[], 'q_abs':[], 'wealth':[], 'stale':[]}
    eventcount=np.zeros(paths,dtype=int); unschedcount=np.zeros(paths,dtype=int)
    for i in range(c.nt):
        p=g.p[pidx]; h=g.h[i]*(1-s); ext=g.rate[pidx]+c.lambda_u+h
        db=np.stack([g.db[pidx,pol['actions'][i,s,pidx,q[j]+c.qmax,0]] for j,pol in enumerate(policies)])
        da=np.stack([g.da[pidx,pol['actions'][i,s,pidx,q[j]+c.qmax,1]] for j,pol in enumerate(policies)])
        lb=c.A*np.exp(-c.k*db)*(q<c.qmax)
        la=c.A*np.exp(-c.k*da)*(q>-c.qmax)
        var=g.var[pidx]+(c.lambda_u*c.rho_u**2+h*c.rho_s**2)*p*(1-p)
        risk += c.gamma*q*q*var[None,:]*g.dt
        integrated_q2 += q*q*g.dt
        # Shared exogenous step. Conditional ordinary-fill draws preserve each
        # controller's marginal full Euler transition probabilities lambda*dt.
        u=rng.random(paths); flow=rng.random(paths)
        kernel_u=rng.random(paths); rounding=rng.random(paths); pick_u=rng.random(paths)
        rd=.5*g.rate[pidx]*g.dt
        down=u<rd; up=(u>=rd)&(u<2*rd)
        unsched=(u>=2*rd)&(u<2*rd+c.lambda_u*g.dt)
        sched=(u>=2*rd+c.lambda_u*g.dt)&(u<ext*g.dt)
        news=unsched|sched
        quiet=u>=ext*g.dt
        flow=flow[None,:]*(1-ext[None,:]*g.dt)
        buy=quiet[None,:]&(flow<lb*g.dt)
        sell=quiet[None,:]&(flow>=lb*g.dt)&(flow<(lb+la)*g.dt)
        cash -= buy*(p[None,:]-db)
        cash += sell*(p[None,:]+da)
        q += buy.astype(int)-sell.astype(int)
        spread_income += buy*db+sell*da
        ordinary += buy|sell
        # Exogenous news cannot coincide with ordinary fills in one Euler step.
        if news.any():
            event_q[:,sched]=q[:,sched]
            event_times[sched]=i*g.dt
            eventcount += sched
            unschedcount += unsched
            rho=np.where(sched,c.rho_s,c.rho_u)
            dest=np.where(kernel_u<p,p+rho*(1-p),(1-rho)*p)
            ib=news[None,:]&(dest[None,:]<p[None,:]-db-1e-12)&(q<c.qmax)&(pick_u[None,:]<c.chi)
            ia=news[None,:]&(dest[None,:]>p[None,:]+da+1e-12)&(q>-c.qmax)&(pick_u[None,:]<c.chi)
            cash -= ib*(p[None,:]-db)
            cash += ia*(p[None,:]+da)
            q += ib.astype(int)-ia.astype(int)
            stale_loss += ib*(p[None,:]-db-dest[None,:])+ia*(dest[None,:]-p[None,:]-da)
            picked += ib|ia
            z=dest*(c.np_-1); lo=np.floor(z).astype(int)
            newidx=np.minimum(lo+(rounding<z-lo),c.np_-1)
            pidx[news]=newidx[news]
            s[sched]=1
        pidx[down]-=1; pidx[up]+=1
        assert np.max(np.abs(q))<=c.qmax
        if i%max(1,c.nt//200)==0:
            trace['t'].append((i+1)*g.dt)
            trace['q_abs'].append(np.abs(q).mean(axis=1).tolist())
            trace['wealth'].append((cash+q*g.p[pidx][None,:]).mean(axis=1).tolist())
            trace['stale'].append(stale_loss.mean(axis=1).tolist())
    p=g.p[pidx]; Y=rng.random(paths)<p
    marked=cash+q*p[None,:]; settled=cash+q*Y[None,:]
    terminal=c.gamma_T*q*q*p[None,:]*(1-p[None,:])
    objective=marked-risk-terminal
    summary={'tag':tag,'config':asdict(c),'paths':paths,'seed':seed,'controllers':{},'trace':trace,
             'event_frequency':float((eventcount>0).mean()),
             'event_frequency_target':float(1-np.prod(1-g.h*g.dt)),
             'mean_terminal_probability':mean_ci(p),'mean_unscheduled_count':float(unschedcount.mean()),
             'max_scheduled_events':int(eventcount.max())}
    arrays={}
    for j,pol in enumerate(policies):
        name=pol['name']
        metrics={'marked_wealth':marked[j],'settled_wealth':settled[j],'objective':objective[j],
                 'ordinary_spread_income':spread_income[j],'stale_loss':stale_loss[j],
                 'risk_penalty':risk[j],'terminal_penalty':terminal[j],
                 'ordinary_fills':ordinary[j],'stale_fills':picked[j],
                 'inventory_exposure':integrated_q2[j], 'event_abs_inventory':np.abs(event_q[j,np.isfinite(event_q[j])])}
        summary['controllers'][name]={k:mean_ci(v) for k,v in metrics.items()}
        summary['controllers'][name]['settled_wealth_q05']=float(np.quantile(settled[j],.05))
        summary['controllers'][name]['settled_wealth_es05']=float(np.sort(settled[j])[:max(1,paths//20)].mean())
        summary['controllers'][name]['loss_probability']=float((settled[j]<0).mean())
        summary['controllers'][name]['own_model_value']=pol['value']
        for k,v in metrics.items():
            arrays[name+'_'+k]=v
    for key in ['objective','marked_wealth','settled_wealth','stale_loss','inventory_exposure']:
        summary.setdefault('paired_differences',{})[key]=mean_ci(arrays['ea_'+key]-arrays['fn_'+key])
    np.savez_compressed(ROOT/'results'/f'{tag}_samples.npz',**arrays)
    (ROOT/'results'/f'{tag}.json').write_text(json.dumps(summary,indent=2))
    print(f"Simulated {tag}: {paths} paths; paired objective {summary['paired_differences']['objective']}",flush=True)
    return summary

def diagnostics():
    c=Config(np_=21,nt=500,qmax=2,action_step=.02,event_mass=0,lambda_u=0)
    fn=solve(c,'fn'); ea=solve(c,'ea')
    assert abs(fn['value']-ea['value'])<1e-12
    assert np.array_equal(fn['actions'],ea['actions'])
    g=Grid(Config())
    for rho, (dest,lo,w,prob) in zip([g.c.rho_u,g.c.rho_s],g.kernels):
        assert np.allclose((dest*prob).sum(0),g.p)
        assert np.allclose(((dest-g.p)**2*prob).sum(0),rho*rho*g.p*(1-g.p))
        assert np.allclose(((lo+w)/(g.c.np_-1)),dest)
    # Simultaneous jump/fill accounting for both sides, and strict equality.
    for p,pnew,b,a,q in [(.5,.2,.45,.55,2),(.5,.8,.45,.55,-2),(.5,.55,.45,.55,1)]:
        ib=int(pnew<b-1e-12); ia=int(pnew>a+1e-12)
        qp=q+ib-ia; xp=-b*ib+a*ia
        assert np.isclose(xp+qp*pnew-q*p,q*(pnew-p)+(pnew-b)*ib+(a-pnew)*ia)
    print('Diagnostics passed: zero-news policy identity, kernels, interpolation, event accounting.',flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--paths',type=int,default=30000)
    parser.add_argument('--skip-refinement',action='store_true'); args=parser.parse_args()
    (ROOT/'results').mkdir(exist_ok=True); diagnostics()
    c=Config(); fn=solve(c,'fn'); ea=solve(c,'ea')
    summary=simulate([fn,ea],c,args.paths)
    exact={'fn':evaluate(fn,c),'ea':ea['value']}
    summary['true_environment_values']=exact
    checks={}
    for name in exact:
        mc=summary['controllers'][name]['objective']
        z=(mc['mean']-exact[name])/mc['se']
        checks[name]={'z_score':z,'passes_4se':abs(z)<4}
        assert abs(z)<4, (name,mc,exact[name])
    summary['bellman_mc_checks']=checks
    (ROOT/'results'/'main.json').write_text(json.dumps(summary,indent=2))
    # Keep a compact policy slice for plotting, avoiding large policy artifacts.
    g=fn['grid']; pi=c.np_//2; qi=c.qmax
    np.savez_compressed(ROOT/'results'/'policy_slices.npz',t=g.t,h=g.h,
        fn_spread=g.db[pi,fn['actions'][:,0,pi,qi,0]]+g.da[pi,fn['actions'][:,0,pi,qi,1]],
        ea_pending=g.db[pi,ea['actions'][:,0,pi,qi,0]]+g.da[pi,ea['actions'][:,0,pi,qi,1]],
        ea_completed=g.db[pi,ea['actions'][:,1,pi,qi,0]]+g.da[pi,ea['actions'][:,1,pi,qi,1]])
    half=replace(c,chi=.5); ea_half=solve(half,'ea')
    simulate([fn,ea_half],half,args.paths,seed=20261015,tag='partial_pickoff')
    refinement=[]
    if not args.skip_refinement:
        for cfg in [replace(c,np_=41,nt=2000,action_step=.01),
                    replace(c,np_=121,nt=8000,action_step=.0025)]:
            f=solve(cfg,'fn'); e=solve(cfg,'ea')
            ftrue=evaluate(f,cfg)
            refinement.append({'np':cfg.np_,'nt':cfg.nt,'action_step':cfg.action_step,
                               'fn_own':f['value'],'fn_true':ftrue,'ea_true':e['value'],
                               'advantage':e['value']-ftrue})
        (ROOT/'results'/'refinement.json').write_text(json.dumps(refinement,indent=2))
    print('Study complete.',flush=True)

if __name__=='__main__':
    main()
