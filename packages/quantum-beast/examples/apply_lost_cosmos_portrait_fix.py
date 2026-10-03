"""Optional presentation-only fix for the pinned existing LOST COSMOS engine.

Run only in an isolated imported build. No game state, saves, rules, BCP1 or
model code changes. Refuses every source other than the exact reviewed engine.
"""
import argparse,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('isolated_source',type=Path);args=ap.parse_args()
p=args.isolated_source/'lost_cosmos_v5.c';raw=p.read_bytes()
if hashlib.sha256(raw).hexdigest()!='7d7e60d166e463bbec1035f9ba97218b33f92a97fcf72d21c0e5e74ec28e4be3':
 raise SystemExit('Refusing an unrecognized engine. Use the pinned committed source in an isolated copy.')
text=raw.decode()
marker='static void render(void){'
helper='''/* QBEAST: render the imported roster once per actual roster change. The
   original repeated clears cross active scanlines and erase its upper rows.
   Blank only the redraw, retain the map, and update OBJ in normal VBlank. */
static int lc_bridge_collection_render(void){
#if defined(LC_IMPORTED_COMPANION)
 static u32 previous=0;static u8 visible=0;
 if(game_mode==MODE_PAUSE&&pause_page==18){
  u32 key=2166136261u;unsigned i;const u8 *bytes=(const u8*)&lc_party;
  for(i=0;i<sizeof(lc_party);i++)key=(key^bytes[i])*16777619u;
  key=(key^lc_party_sel)*16777619u;key=(key^lc_release_armed)*16777619u;
  if(!visible||key!=previous){
   u16 display=REG_DISPCNT;REG_DISPCNT=(u16)(display|128u);
   oam_hide_all();draw_pause();
   REG_BG1CNT=(u16)((REG_BG1CNT&~3u)|1u); /* OBJ above opaque UI */
   wait_vblank();REG_DISPCNT=display;previous=key;visible=1;
  }else lc_draw_import_portrait(168,64);
  return 1;
 }
 if(visible){REG_BG1CNT=(u16)(REG_BG1CNT&~3u);visible=0;}
#endif
 return 0;
}
'''
assert text.count(marker)==1
text=text.replace('ui_text(18,8,"BB PIXEL",13);','ui_text(18,3,"BB PIXEL",13);').replace('lc_draw_import_portrait(168,82);','lc_draw_import_portrait(168,64);')
text=text.replace(marker,helper+marker+'if(lc_bridge_collection_render())return;')
p.write_text(text)
print('Applied bounded imported-roster presentation fix; original game/save mechanics preserved. Engine SHA256 '+hashlib.sha256(p.read_bytes()).hexdigest())
