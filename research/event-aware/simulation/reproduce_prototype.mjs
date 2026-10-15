/** Run the computational functions in index.html verbatim, without a browser.
 * No rendering code or event handlers are executed. Source hashes and default
 * inputs are saved so the paper illustration can be traced to the prototype.
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert.equal(scripts.length,1,'Expected the standalone prototype computational script');
const script=scripts[0][1];
const cutoff=script.indexOf('      function svgEl(');
assert(cutoff>0,'Could not locate the end of prototype computation');
const params={};
for(const id of ['tau','width','rhoS','lambdaU','rhoU','q0','seed']){
  const tag=html.match(new RegExp(`<input\\b[^>]*\\bid="${id}"[^>]*>`));
  assert(tag,`Missing input ${id}`);
  const value=tag[0].match(/\bvalue="([^"]+)"/);
  assert(value,`Missing default for ${id}`);
  params[id]=Number(value[1]);
}
function compute(){
  const context=vm.createContext({params});
  vm.runInContext(script.slice(0,cutoff)+`
    const policies=solvePolicies(params);
    globalThis.result={params, grid:{N,P,QN,qMin,qMax,pMin,pMax,pStep,dt,offsets,
      sigma,gamma,gammaT,fillA,fillK}, simulation:simulate(params,policies)};
  })();`,context,{timeout:120000});
  return JSON.parse(JSON.stringify(context.result));
}
const output=compute();
assert.deepEqual(output,compute(),'Fixed-seed prototype reproduction must be deterministic');
const {simulation:s,grid:g}=output;
assert.equal(s.p.length,g.N+1);
for(const key of ['orig','aware']){
  for(const series of ['bid','ask','q','pnl','spread']) assert.equal(s[key][series].length,g.N);
  assert(s[key].q.every(q=>q>=g.qMin&&q<=g.qMax));
  assert(Math.abs(s.makers[key].cash+s.makers[key].q*s.p.at(-1)-s[key].pnl.at(-1))<1e-12);
}
assert(s.p.every(p=>p>=g.pMin&&p<=g.pMax));
assert.equal(s.eventKind.filter(k=>k==='scheduled').length,s.eventIndex===null?0:1);
output.source_sha256=crypto.createHash('sha256').update(html).digest('hex');
output.script_sha256=crypto.createHash('sha256').update(script).digest('hex');
output.node_version=process.version;
output.source='index.html';
fs.mkdirSync(path.join(root,'results'),{recursive:true});
fs.writeFileSync(path.join(root,'results/prototype_path.json'),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({params,eventIndex:s.eventIndex,eventTime:(s.eventIndex+1)/g.N,
 finalPnl:{orig:s.orig.pnl.at(-1),aware:s.aware.pnl.at(-1)},
 pickoff:{orig:s.makers.orig.pickoff,aware:s.makers.aware.pickoff},
 validation:'Deterministic replay, bounds, dimensions, and terminal accounting passed.'},null,2));
