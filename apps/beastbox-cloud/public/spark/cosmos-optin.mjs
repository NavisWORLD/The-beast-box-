/** My Beast: explicit "Grow in the cosmos" opt-in (public profile only). Same API as the Beast Cage. */
import {publicProfileFromBeast} from './cosmos-profile.mjs';

let lastId=null;
export async function renderCosmos(beast,name){
 const box=document.getElementById('cosmos-optin');if(!box||!beast)return;
 const profile=publicProfileFromBeast(beast,{name});
 if(!profile||!profile.id){box.hidden=true;return;}
 box.hidden=false;lastId=profile.id;
 const text=box.querySelector('[data-cosmos-text]'),btn=box.querySelector('button'),note=box.querySelector('[data-cosmos-note]');
 btn.disabled=true;note.textContent='';text.textContent='Checking the cosmos…';
 let st={configured:false};
 try{const r=await fetch(`/api/cosmos/beasts/${encodeURIComponent(profile.id)}`,{cache:'no-store'});st=await r.json();}catch{}
 if(lastId!==profile.id)return;
 if(!st.configured){text.textContent='Storage not configured yet. Per-beast cosmos folders open once the owner connects Azure storage. Your beast keeps living in this browser.';box.dataset.cosmosState='not-configured';return;}
 if(st.registered){text.textContent=`✓ ${profile.name} is growing in the cosmos${st.diary?` · tick ${st.diary.tick} · ${st.diary.stage_name}`:' · waiting for its first loop tick'}.`;box.dataset.cosmosState='registered';return;}
 box.dataset.cosmosState='ready';
 text.textContent=`Let the scheduled loop grow ${profile.name} while you are away (free Rigetti simulator, simulated). Shares only: id, name, seed provenance (${profile.provenance.backend} run), visual traits and game stats. Never chats, owner memory or keeper names.`;
 btn.disabled=false;
 btn.onclick=async()=>{
  btn.disabled=true;note.textContent='Registering…';
  try{const r=await fetch('/api/cosmos/beasts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile})});const d=await r.json();
   note.textContent=d.ok?(d.already?'Already growing in the cosmos.':'Registered. It will grow in small batches, about every 30 minutes.'):(d.error||'Could not register.');
   if(d.ok)box.dataset.cosmosState='registered';else btn.disabled=false;}
  catch{note.textContent='Could not reach the cosmos.';btn.disabled=false;}
 };
}
