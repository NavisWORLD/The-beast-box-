/* Include generated companion_assets.h from the downloaded ZIP next to this file.
 * Integrate into an existing devkitARM GBA game; this is not a complete ROM.
 * Your game is responsible for vblank timing, OBJ palette/tile allocation,
 * saving an approved snapshot, and any permitted external serial bridge. */
#include <stdint.h>
#include "beast_companion.h"
#include "companion_assets.h"
#define REG_VCOUNT (*(volatile uint16_t *)(uintptr_t)0x04000006u)
static void wait_vblank(void){
 while(REG_VCOUNT>=160u){} while(REG_VCOUNT<160u){}
}
int main(void){
 beast_mood_t mood=BEAST_IDLE;
 /* The generated asset arrays contain only public character pixels/palette. */
 if(!beast_install(beast_tiles,sizeof(beast_tiles),beast_palette))for(;;){}
 for(;;){
  wait_vblank();
  /* Example: your game maps player controls or pre-approved numeric events
     into moods. No autonomous tool, network, microphone or model privileges. */
  beast_show((uint8_t)mood,88u,48u);
 }
}
