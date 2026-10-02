#ifndef BEAST_COMPANION_H
#define BEAST_COMPANION_H
/* BEAST BOX / CORY DAVIS. Import-only GBA character, no model inference. */
#include <stdint.h>
#define BEAST_FRAME_BYTES 2048u
#define BEAST_TILE_BYTES 8192u
#define BEAST_PALETTE_ENTRIES 16u
#define BEAST_SNAPSHOT_BYTES 60u
typedef enum {
 BEAST_IDLE=0, BEAST_LISTENING=1, BEAST_THINKING=2, BEAST_CELEBRATING=3
} beast_mood_t;
typedef struct {
 uint8_t look_id;
 uint8_t measured; /* 0=visual-only; 1=explicit checkpoint-backed data */
 uint32_t sequence;
 int16_t cns_q8_8[12];      /* generic numeric software state, NOT hardware perception */
 int16_t synaptic_q8_8[12]; /* from opt-in authenticated COSMOS trace */
} beast_soul_t;
/* Safe for game code to call; these functions never issue model/tool actions. */
int beast_read_snapshot(const uint8_t *data,uint32_t length,beast_soul_t *out);
uint8_t beast_visual_energy(const beast_soul_t *soul);
/* GBA mode 0 OBJ 1D 4bpp rendering. Run from a game with 64 free OBJ tiles
   per animation frame and unused OBJ sprite index 0. No dynamic allocation. */
int beast_install(const uint8_t *tiles,uint32_t length,const uint16_t *palette);
void beast_show(uint8_t frame,uint16_t x,uint16_t y);
#endif
