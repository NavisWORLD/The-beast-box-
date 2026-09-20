"""Read-only local dashboard: all panels reflect verified recorded events."""
from __future__ import annotations
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from recorder import verify_ledger

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>i dare you // experiment ledger</title>
<style>
:root{color-scheme:dark;font:15px system-ui;background:#090e1e;color:#ecf4ff}
body{margin:0 auto;max-width:1350px;padding:20px}
header,section{background:#121d33;border:1px solid #344e6c;border-radius:16px;padding:18px}
header{margin-bottom:16px}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
section:last-child{grid-column:1/-1}h1{font-size:32px}h2{color:#85e8f4;font-size:19px}
.warn{color:#ffd18d}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#090e1e;padding:12px;font-size:12px}
#scrub{width:100%}button{background:#254361;color:white;border:1px solid #6387a4;border-radius:7px;padding:9px;cursor:pointer}
@media(max-width:750px){main{grid-template-columns:1fr}section:last-child{grid-column:auto}}
</style></head>
<body><header><h1>CORY DAVIS // i dare you 💀</h1>
<p class="warn">Actual recorded events only. This is not proof of a JEV ↔ PHOS swap. Private JEV evidence is excluded.</p>
<p id="status">Loading ledger…</p><input id="scrub" type="range" min="0" max="0" value="0" aria-label="Timeline">
<button id="prev">Previous</button><button id="next">Next</button><button id="latest">Latest</button></header>
<main><section><h2>1 // CONVERSATION / DECISIONS</h2><div id="conversation"></div></section>
<section><h2>2 // PHOS TRAINING</h2><div id="training"></div></section>
<section><h2>3 // ACTIVE MODEL</h2><div id="model"></div></section>
<section><h2>4 // PERSISTENT SYSTEM STATE</h2><div id="state"></div></section>
<section><h2>5 // RESULTS AND TIMELINE</h2><div id="results"></div></section></main>
<script>
let events=[],current=0;
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const find=(list,kind)=>list.filter(e=>e.event_type===kind);
function render(){
 const active=events.slice(0,current+1), last=active.at(-1), responses=find(active,'model_response'),
   steps=find(active,'training_step'), blocked=find(active,'phase_blocked'), snapshots=find(active,'independent_state_written'),
   checkpoints=find(active,'checkpoint_verified'), swaps=find(active,'provider_swapped');
 $('scrub').max=Math.max(events.length-1,0);$('scrub').value=current;
 $('status').textContent=last?last.timestamp+' · '+last.phase+' / '+last.event_type+' · '+(current+1)+'/'+events.length:'No events';
 $('conversation').innerHTML=responses.length?responses.map(e=>'<pre>'+esc(e.payload.provider)+' @ '+esc(e.timestamp)+'\n'+esc(e.payload.input)+'\n'+esc(e.payload.output)+'</pre>').join(''):'No generated conversation recorded. JEV typed decisions remain private.';
 $('training').innerHTML=steps.length?steps.map(e=>'<pre>'+esc(JSON.stringify(e.payload,null,2))+'</pre>').join(''):'<p class="warn">No verified training steps, loss or held-out validation metrics.</p>';
 $('model').innerHTML='<p>Planned JEV → PHOS → trained PHOS → JEV</p><p>Verified provider transitions: '+swaps.length+'</p>'+blocked.map(e=>'<p class="warn">'+esc(e.phase)+': '+esc(e.payload.reason)+'</p>').join('');
 $('state').innerHTML=snapshots.map(e=>'<p>'+esc(e.timestamp)+' · memory: '+esc(e.payload.memory_count)+' · counter: '+esc(e.payload.state_counter)+'</p><pre>'+esc(JSON.stringify(e.payload.dyn12))+'</pre>').join('')+(checkpoints.length?'<p>Checkpoint digest: '+esc(checkpoints.at(-1).payload.sha256)+'</p>':'');
 $('results').innerHTML=active.map(e=>'<pre>#'+e.seq+' · '+esc(e.timestamp)+' · '+esc(e.phase)+' / '+esc(e.event_type)+'\n'+esc(JSON.stringify(e.payload))+'</pre>').join('');
}
function goto(i){current=Math.max(0,Math.min(i,events.length-1));render()}
$('scrub').oninput=e=>goto(Number(e.target.value));
$('prev').onclick=()=>goto(current-1);$('next').onclick=()=>goto(current+1);$('latest').onclick=()=>goto(events.length-1);
async function refresh(){try{const res=await fetch('/events.jsonl',{cache:'no-store'});if(!res.ok)throw Error(res.status);const value=(await res.text()).trim();const next=value?value.split('\n').map(JSON.parse):[];const tail=current>=events.length-1;events=next;if(tail)current=Math.max(0,events.length-1);render()}catch(e){$('status').textContent='Ledger unavailable: '+e.message}}
refresh();setInterval(refresh,1500);
</script></body></html>"""


def serve(run, port=8088):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/', '/index.html'):
                body, mime = HTML.encode('utf-8'), 'text/html; charset=utf-8'
            elif self.path == '/events.jsonl':
                try:
                    verify_ledger(run / 'events.jsonl')
                    body = (run / 'events.jsonl').read_bytes()
                except (ValueError, OSError) as exc:
                    self.send_error(409, str(exc))
                    return
                mime = 'application/x-ndjson'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = HTTPServer(('127.0.0.1', port), Handler)
    print('Local dashboard: http://127.0.0.1:'+str(server.server_port), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--port', type=int, default=8088)
    args=parser.parse_args()
    serve(args.run, args.port)
