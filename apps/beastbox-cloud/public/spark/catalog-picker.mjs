/** Quantum catalogue picker: all entries in /spark/catalog-index.json (one per recorded IBM count
 * distribution, SIMULATED 'balanced' signal). Pure helpers are exported for tests. */
export const CATALOG_PATH='/spark/catalog-index.json';
export function rowsOf(cat){
 const T=cat.traits;return cat.rows.map(r=>{const o={key:r[0],name:r[1],finalName:r[2],bits:r[3]};T.forEach((t,i)=>{o[t]=cat.values[t][r[4+i]];});return o;});
}
export function filterRows(rows,{island='',body='',q='',sort='rarest'}={}){
 const s=q.trim().toLowerCase();
 const out=rows.filter(r=>(!island||r.island===island)&&(!body||r.body===body)&&(!s||r.key.toLowerCase().includes(s)||r.name.toLowerCase().includes(s)||r.finalName.toLowerCase().includes(s)||r.temperament.toLowerCase().includes(s)));
 if(sort==='rarest')out.sort((a,b)=>b.bits-a.bits||a.key.localeCompare(b.key));
 else if(sort==='common')out.sort((a,b)=>a.bits-b.bits||a.key.localeCompare(b.key));
 else if(sort==='name')out.sort((a,b)=>a.name.localeCompare(b.name)||a.key.localeCompare(b.key));
 return out;
}
/** Uniform over the whole catalogue (or the given list) with crypto randomness and rejection sampling. */
export function randomRow(rows,rand32=()=>crypto.getRandomValues(new Uint32Array(1))[0]){
 if(!rows.length)return null;const n=rows.length,lim=Math.floor(4294967296/n)*n;let x;do{x=rand32()>>>0;}while(x>=lim);return rows[x%n];
}
/** Rarest unseen traits: maximise self-information of trait values the keeper does not own yet. */
export function uniqueRow(rows,cat,ownedGenomes=[]){
 const T=cat.traits,N=cat.count,owned=Object.fromEntries(T.map(t=>[t,new Set(ownedGenomes.map(g=>g?.[t]).filter(Boolean))]));
 const ownedKeys=new Set(ownedGenomes.map(g=>g?.inputs?.quantum_run).filter(Boolean));
 const info=(t,v)=>-Math.log2(cat.counts[t][cat.values[t].indexOf(v)]/N);
 let best=null,score=-1;
 for(const r of rows){if(ownedKeys.has(r.key))continue;const s=T.reduce((a,t)=>a+(owned[t].has(r[t])?0:info(t,r[t])),0);if(s>score||(s===score&&r.key<best.key)){score=s;best=r;}}
 return best?{row:best,novelBits:Math.round(score*100)/100,newTraits:T.filter(t=>!owned[t].has(best[t])).map(t=>`${t}: ${best[t]}`)}:null;
}
export function mountPicker(root,cat,{onPick,owned}){
 const rows=rowsOf(cat),el=(tag,attrs={},text='')=>{const e=document.createElement(tag);Object.assign(e,attrs);if(text)e.textContent=text;return e;};
 const opt=(v,t)=>el('option',{value:v},t);
 const island=el('select',{id:'cat-island','aria-label':'Island'});island.append(opt('','All islands'),...cat.values.island.map(v=>opt(v,`${v} (${cat.counts.island[cat.values.island.indexOf(v)]})`)));
 const body=el('select',{id:'cat-body'});body.append(opt('','All body plans'),...cat.values.body.map(v=>opt(v,`${v} (${cat.counts.body[cat.values.body.indexOf(v)]})`)));
 const sort=el('select',{id:'cat-sort'});sort.append(opt('rarest','Rarest first'),opt('common','Most common first'),opt('name','Name A–Z'),opt('catalogue','Catalogue order'));
 const q=el('input',{id:'cat-q',type:'search',placeholder:'Name, temperament or IBM job',autocomplete:'off'});
 island.setAttribute('aria-label','Island');body.setAttribute('aria-label','Body plan');sort.setAttribute('aria-label','Sort');q.setAttribute('aria-label','Search catalogue');
 const random=el('button',{type:'button',id:'cat-random'},'🎲 Random');const unique=el('button',{type:'button',id:'cat-unique'},'✦ Unique');
 const info=el('p',{id:'cat-info',className:'hint'}),list=el('ol',{id:'cat-list',className:'cat-list'}),more=el('button',{type:'button',id:'cat-more'},'Show more');
 let shown=24,current=[];
 const card=(r,note='')=>{const li=el('li');const b=el('button',{type:'button',className:'cat-row'});b.dataset.key=r.key;
  b.append(el('b',{},r.name),el('span',{},` → ${r.finalName}`),el('small',{},` ${r.body} · ${r.island.replace(/^The /,'')} · ${r.temperament} · ${r.bits} bits${note?' · '+note:''}`));
  b.addEventListener('click',()=>onPick(r,note));li.append(b);return li;};
 const draw=()=>{current=filterRows(rows,{island:island.value,body:body.value,q:q.value,sort:sort.value});list.replaceChildren(...current.slice(0,shown).map(r=>card(r)));more.hidden=current.length<=shown;
  info.textContent=`${current.length} of ${cat.count} catalogue beasts · rarity = trait self-information · seeds are recorded historical IBM counts · signal SIMULATED (balanced)`;};
 for(const c of [island,body,sort])c.addEventListener('change',()=>{shown=24;draw();});q.addEventListener('input',()=>{shown=24;draw();});more.addEventListener('click',()=>{shown+=24;draw();});
 random.addEventListener('click',()=>{const r=randomRow(rows);info.textContent=`Random: uniform over all ${rows.length} catalogue beasts → ${r.name}`;onPick(r,'random');});
 unique.addEventListener('click',()=>{const u=uniqueRow(rows,cat,owned());if(!u)return;info.textContent=`Unique: ${u.row.name} brings ${u.novelBits} bits of traits you don't own yet (${u.newTraits.slice(0,4).join(', ')})`;onPick(u.row,'unique');});
 const filters=el('div',{className:'cat-filters'});filters.append(island,body,sort,q);const actions=el('div',{className:'row'});actions.append(random,unique);
 root.replaceChildren(filters,actions,info,list,more);draw();return {rows,draw};
}
