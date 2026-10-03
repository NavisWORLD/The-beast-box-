"""Read-only diagnosis of the exported Beast in actual native libmGBA gameplay.

All progression uses ordinary controller input; no savestates or memory writes.
Requires the existing LOST COSMOS tools and an isolated native build.
"""
import argparse,json,struct,sys,zipfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--game-tools',type=Path,required=True);ap.add_argument('--rom',type=Path,required=True);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--export-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
sys.path.insert(0,str(args.game_tools.resolve()))
from mgba import Mgba,sha256
args.output.mkdir(parents=True,exist_ok=True);save=args.output/'imported-beast.sav'
if save.exists():raise RuntimeError('Use a new evidence directory; never overwrite an existing battery save')
with zipfile.ZipFile(args.export_zip) as z:profile=json.loads(z.read('companion.profile.json'));tiles=z.read('gba/companion_tiles.4bpp');palette=z.read('gba/companion_palette.bgr555')
identity=int(profile['id'][3:],16)
def wait(e,fn,budget=900):
 for _ in range((budget+7)//8):
  if fn():return
  e.step((),8)
 raise AssertionError('Timed out waiting for native controller transition')
def roster(e):
 s=e.symbols['lc_party'];raw=e.read_range(s.address,24)
 return {'count':raw[0],'active':raw[1],'species':raw[4],'stage':raw[5],'level':raw[6],'bond':raw[7],'hp':struct.unpack_from('<H',raw,8)[0],'identity':struct.unpack_from('<I',raw,12)[0],'seed':struct.unpack_from('<I',raw,16)[0],'attack':raw[20],'defense':raw[21]}
def position(e):
 if 'player' in e.symbols:return [e.read_symbol('player',width=2,signed=True),e.read_symbol('player',width=2,offset=2,signed=True)]
 return [e.read_symbol('player.0',signed=True),e.read_symbol('player.1',signed=True)]
def collection(e):
 e.tap('START',hold=12,release=12);wait(e,lambda:e.read_symbol('game_mode')==2)
 e.tap('DOWN',hold=12,release=12);e.tap('A',hold=12,release=12)
 assert e.read_symbol('pause_page')==2
 e.tap('R',hold=12,release=12);assert e.read_symbol('pause_page')==18
 e.step((),60)
def visible_portrait(e):
 oam=e.read_range(0x07000000+42*8,6);y,x,tile=struct.unpack('<3H',oam)
 assert (x&511)==168 and (y&255)==64
 index=(tile&1023)-640;assert index in (0,64,128,192)
 assert e.read_range(0x06010000+640*32,8192)==tiles
 assert e.read_range(0x05000200+15*32,32)==palette
 rgb=e.rgb();matches=opaque=0
 for py in range(64):
  for px in range(64):
   off=index*32+((py//8)*8+px//8)*32+(py%8)*4+(px%8)//2
   color=(tiles[off]>>((px%2)*4))&15
   if not color:continue
   opaque+=1;value=struct.unpack_from('<H',palette,color*2)[0]
   expected=[round(((value>>shift)&31)*255/31) for shift in (0,5,10)]
   at=((py+64)*240+px+168)*3
   if all(abs(rgb[at+k]-expected[k])<=7 for k in range(3)):matches+=1
 assert opaque>200 and matches/opaque>.90,(opaque,matches)
 return {'opaque_art_pixels':opaque,'matching_visible_pixels':matches,'sprite_frame':index//64,'actual_obj_vram_and_palette_match':True}
def leave(e):
 # Collection B returns to COSMOS, then the root pause page, then exploration.
 for _ in range(4):
  if e.read_symbol('game_mode')==0:break
  e.tap('B',hold=12,release=12)
 wait(e,lambda:e.read_symbol('game_mode')==0)
report={'schema':'qbeast-real-native-gba-import-v1','rom_sha256':sha256(args.rom),'elf_sha256':sha256(args.elf),'export_zip_sha256':sha256(args.export_zip),'creature_id':profile['id'],'memory_writes':False,'savestate_loads':False,'full_campaign':False,'physical_iPhone_test':False}
with Mgba(args.rom,elf=args.elf,save_path=save,trace_path=args.output/'boot1-inputs.jsonl') as e:
 report['emulator']=e.metadata;e.start_recording(args.output/'native-beast-boot1.mp4');e.step((),180);assert e.read_symbol('v10_has_save')==0;e.screenshot(args.output/'01-title.png')
 e.tap('A',hold=12,release=12);wait(e,lambda:e.read_symbol('v10_opening')==1)
 for _ in range(40):
  if not e.read_symbol('v10_opening'):break
  e.tap('A',hold=12,release=12)
 wait(e,lambda:e.read_symbol('v10_opening')==0);assert e.read_symbol('current_room')==2
 # Opening completion performs the original synchronous SRAM journal before
 # returning to the main input loop. A flag becoming zero is earlier than
 # controller readiness; wait for a real new game frame, never inject state.
 last_frame=e.read_symbol('frame');wait(e,lambda:e.read_symbol('frame')!=last_frame)
 first=roster(e);assert first['count']==1 and first['identity']==identity and first['species']==128 and first['level']==1 and first['stage']==0
 collection(e);report['visible_portrait_boot1']=visible_portrait(e);e.screenshot(args.output/'02-imported-beast-collection.png')
 # Read the actual imported tile bytes/palette in cartridge ROM; no state edits.
 assert e.read_range(e.symbols['lc_imported_companion_tiles'].address,8192)==tiles
 assert e.read_range(e.symbols['lc_imported_companion_palette'].address,32)==palette
 leave(e);original=position(e)
 for direction in ['RIGHT','DOWN','LEFT','UP']:
  e.step(direction,24);e.step((),12)
  if position(e)!=original:break
 moved=position(e);assert moved!=original
 e.tap('START',hold=12,release=12);wait(e,lambda:e.read_symbol('game_mode')==2)
 # Pause selection is retained from the COSMOS page (row 1).
 for _ in range(13):
  if e.read_symbol('pause_sel')==9:break
  e.tap('DOWN',hold=12,release=12)
 assert e.read_symbol('pause_sel')==9;e.tap('A',hold=12,release=12);wait(e,lambda:e.read_symbol('pause_page')==10,600)
 leave(e);report['boot1_roster']=roster(e);report['controller_earned_position']=moved;report['capture1']=e.stop_recording()
assert save.read_bytes()[:4]==b'LCV5';report['save_sha256']=sha256(save)
with Mgba(args.rom,elf=args.elf,save_path=save,trace_path=args.output/'boot2-inputs.jsonl') as e:
 e.start_recording(args.output/'native-beast-boot2.mp4');e.step((),180);assert e.read_symbol('v10_has_save')==1
 e.tap('DOWN',hold=12,release=12);assert e.read_symbol('v10_title_sel')==1;e.tap('A',hold=12,release=12);wait(e,lambda:e.read_symbol('intro')==0)
 restored=roster(e);assert restored==report['boot1_roster'];assert position(e)==moved
 last_frame=e.read_symbol('frame');wait(e,lambda:e.read_symbol('frame')!=last_frame)
 collection(e);report['visible_portrait_boot2']=visible_portrait(e);e.screenshot(args.output/'03-restored-beast-collection.png');report['boot2_roster']=restored;report['capture2']=e.stop_recording()
assert report['capture1']['audio_nonzero_samples']>0 and report['capture2']['audio_nonzero_samples']>0
report['verified']=['actual native GBA boot and original opening','real controller navigation into creature roster','exported public identity, family, stats and exact pixel assets loaded','movement through controller inputs','battery save and independent second cold boot restore imported creature and earned position','real native screenshots/video/audio']
(args.output/'native.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS real mGBA imported creature, original assets, controller movement, battery save and two cold boots')
