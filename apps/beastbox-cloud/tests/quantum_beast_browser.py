"""Real built-app desktop/mobile public snapshot and hostile-file acceptance."""
import argparse,json,re,zipfile,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
# Match the existing Genesis/WebGL acceptance budget on CPU-only CI runners.
expect.set_options(timeout=23000)
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--example',type=Path,required=True);args=ap.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[3]
def fixture(script):
 result=subprocess.run(['node','-e',script,str(args.example.resolve())],cwd=root/'packages/quantum-beast',text=True,capture_output=True,check=True)
 return result.stdout.encode()
cosmetic=fixture("const c=require('./dist'),fs=require('fs');(async()=>{const old=await c.parseSnapshot(fs.readFileSync(process.argv[1],'utf8'));const p=old.profile;p.appearance.hueShift++;console.log(await c.serializeSnapshot(await c.createSnapshot(p)));})().catch(e=>{console.error(e);process.exit(1)});")
newer=fixture("const c=require('./dist'),fs=require('fs');(async()=>{const old=await c.parseSnapshot(fs.readFileSync(process.argv[1],'utf8'));const b=await c.BeastBridge.load(old),p=await b.record_event({summary:'We continued the same public adventure.',source_ref:'test:browser-2'});console.log(await c.serializeSnapshot(await c.approveProposal(old,p,{allow:['memory'],public_memory:true})));})().catch(e=>{console.error(e);process.exit(1)});")
def import_package(page,payload):
 control=page.get_by_label('Quantum Beast file')
 # File setters can dispatch changes into disabled controls. Wait for each
 # actual transfer to finish instead of matching a prior identical alert.
 expect(control).to_be_enabled();control.set_input_files(payload)
 try:expect(control).to_be_enabled()
 except Exception:
  page.screenshot(path=str(args.output/'failed-import.png'))
  diagnostics=page.evaluate("async()=>({alerts:[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent),locks:await navigator.locks.query(),storage:localStorage.getItem('beastbox-quantum-beast-public-v1')})")
  (args.output/'failed-import.json').write_text(json.dumps(diagnostics,indent=2)+'\n');print(json.dumps(diagnostics));raise
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-angle=swiftshader'])
 for width,height in [(1440,1000),(390,844),(320,720)]:
  context=browser.new_context(viewport={'width':width,'height':height},accept_downloads=True)
  page=context.new_page();errors=[];private=[]
  page.on('pageerror',lambda x:errors.append(str(x)));page.on('request',lambda r:private.append(r.url) if '/api/bridge' in r.url else None)
  response=page.goto('http://127.0.0.1:3100/beast-cage',wait_until='domcontentloaded');assert response.status==200
  page.get_by_label('Character seed').fill('quantum-beast-first-contact');page.get_by_label('Cosmic family').select_option('nebula');page.get_by_role('button',name='Generate from this seed',exact=True).click()
  with page.expect_download() as pending:page.get_by_role('button',name='DOWNLOAD QUANTUM BEAST',exact=True).click()
  file=args.output/f'beast-{width}.qbeast';pending.value.save_as(file);original=json.loads(file.read_text())
  assert original['profile']['id']=='bb-f5a4cb6d' and original['events']==[]
  import_package(page,str(args.example.resolve()))
  receipt=page.get_by_label('Portable Beast verification');expect(receipt).to_contain_text('1 approved events')
  stored=page.evaluate("localStorage.getItem('beastbox-quantum-beast-public-v1')")
  snapshot=json.loads(json.loads(stored)['text']);assert snapshot['generation']==1
  forged=json.loads(json.dumps(snapshot));forged['profile']['game']['stats']['hp']+=1
  import_package(page,{'name':'forged.qbeast','mimeType':'application/json','buffer':json.dumps(forged).encode()})
  expect(page.get_by_label('Quantum Beast portable companion bridge').get_by_role('alert')).to_contain_text('Forged or malformed');assert page.evaluate("localStorage.getItem('beastbox-quantum-beast-public-v1')")==stored
  import_package(page,str(file))
  expect(page.get_by_label('Quantum Beast portable companion bridge').get_by_role('alert')).to_contain_text('rewind or fork');assert page.evaluate("localStorage.getItem('beastbox-quantum-beast-public-v1')")==stored
  import_package(page,{'name':'cosmetic-rewind.qbeast','mimeType':'application/json','buffer':cosmetic})
  expect(page.get_by_label('Quantum Beast portable companion bridge').get_by_role('alert')).to_contain_text('rewind or fork');assert page.evaluate("localStorage.getItem('beastbox-quantum-beast-public-v1')")==stored
  page.get_by_label('Character seed').fill('a-distinct-browser-creature');page.get_by_role('button',name='Generate from this seed',exact=True).click()
  with page.expect_download():page.get_by_role('button',name='Start a new portable life (backs up previous Beast)',exact=True).click()
  expect(receipt).to_contain_text('0 approved events')
  import_package(page,str(file))
  expect(page.get_by_label('Quantum Beast portable companion bridge').get_by_role('alert')).to_contain_text('rewind or fork')
  import_package(page,str(args.example.resolve()));expect(receipt).to_contain_text('1 approved events')
  page.reload(wait_until='domcontentloaded');expect(receipt).to_contain_text('1 approved events')
  with page.expect_download() as pending:page.get_by_role('button',name='DOWNLOAD QUANTUM BEAST',exact=True).click()
  restored=args.output/f'restored-{width}.qbeast';pending.value.save_as(restored);assert json.loads(restored.read_text())==snapshot
  with page.expect_download() as pending:page.get_by_role('button',name='Export this Beast to GBA',exact=True).click()
  game_zip=args.output/f'beast-{width}-gba.zip';pending.value.save_as(game_zip)
  with zipfile.ZipFile(game_zip) as z:
   assert len(z.read('gba/companion_profile.bin'))==64
   assert json.loads(z.read('companion.profile.json'))==snapshot['profile']
   assert not any('memory' in x or 'events' in x for x in z.namelist())
  size=page.evaluate('({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})');assert size['scroll']<=size['width']+1,size
  page.get_by_label('Quantum Beast portable companion bridge').screenshot(path=str(args.output/f'bridge-{width}.png'))
  # Real two-tab stale writer: B appends; A must not overwrite the advanced save.
  second=context.new_page();second.goto('http://127.0.0.1:3100/beast-cage',wait_until='domcontentloaded')
  expect(second.get_by_label('Portable Beast verification')).to_contain_text('1 approved events')
  import_package(second,{'name':'continued.qbeast','mimeType':'application/json','buffer':newer})
  expect(second.get_by_label('Portable Beast verification')).to_contain_text('2 approved events')
  page.get_by_role('button',name='DOWNLOAD QUANTUM BEAST',exact=True).click()
  expect(page.get_by_label('Quantum Beast portable companion bridge').get_by_role('alert')).to_contain_text('Another tab changed')
  assert json.loads(json.loads(page.evaluate("localStorage.getItem('beastbox-quantum-beast-public-v1')"))['text'])['generation']==2
  second.close()
  assert not errors,errors;assert not private,private
  results.append({'width':width,'download_import_restart':True,'forged_stats_rejected':True,'rewind_rejected':True,'same_id_cosmetic_rewind_rejected':True,'returning_creature_rewind_rejected':True,'stale_tab_rollback_rejected':True,'gba_zip_verified':True,'horizontal_overflow':False,'page_errors':errors,'private_bridge_requests':private})
  context.close()
 browser.close()
(args.output/'browser.json').write_text(json.dumps({'suite':'real-built-browser-quantum-beast','results':results,'physical_iPhone_test':False},indent=2)+'\n')
print('PASS actual public import/export, local restart, hostile inputs and matching GBA at desktop/390px/320px')
