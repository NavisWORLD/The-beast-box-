#include "beast_companion.h"
#include <stddef.h>
/* These are GBA memory-map registers, not portable host graphics code. */
#define BEAST_REG_DISPCNT (*(volatile uint16_t *)(uintptr_t)0x04000000u)
#define BEAST_OBJ_VRAM ((volatile uint16_t *)(uintptr_t)0x06010000u)
#define BEAST_OBJ_PALETTE ((volatile uint16_t *)(uintptr_t)0x05000200u)
#define BEAST_OBJ_OAM ((volatile uint16_t *)(uintptr_t)0x07000000u)
static uint16_t read16(const uint8_t *p) {
 return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static uint32_t read32(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
int beast_read_snapshot(const uint8_t *data,uint32_t length,beast_soul_t *out) {
 uint32_t i;
 if(data==NULL||out==NULL||length!=BEAST_SNAPSHOT_BYTES)return 0;
 if(data[0]!=66u||data[1]!=67u||data[2]!=71u||data[3]!=49u||
    data[4]!=1u||data[5]>2u||data[6]>1u||data[7]!=0u)return 0;
 out->look_id=data[5];out->measured=data[6];
 out->sequence=read32(data+8);
 for(i=0;i<12;i++){
  out->cns_q8_8[i]=(int16_t)read16(data+12u+i*2u);
  out->synaptic_q8_8[i]=(int16_t)read16(data+36u+i*2u);
 }
 if(out->measured==0u){
  if(out->sequence!=0u)return 0;
  for(i=0;i<12;i++)if(out->cns_q8_8[i]!=0||out->synaptic_q8_8[i]!=0)return 0;
 }
 return 1;
}
uint8_t beast_visual_energy(const beast_soul_t *soul) {
 unsigned long sum=0;
 uint32_t i;
 if(soul==NULL||soul->measured!=1u)return 0;
 for(i=0;i<12;i++){
  int32_t val=soul->cns_q8_8[i];
  if(val<0)val=-val;
  sum+=(uint32_t)val;
 }
 sum/=12u;
 /* Clamp displayed effect to 8 bits. This is visual mapping, not intelligence. */
 return (uint8_t)(sum>255u?255u:sum);
}
int beast_install(const uint8_t *tiles,uint32_t length,const uint16_t *palette) {
 uint32_t i;
 if(tiles==NULL||palette==NULL||length!=BEAST_TILE_BYTES)return 0;
 BEAST_REG_DISPCNT=(uint16_t)(BEAST_REG_DISPCNT|0x1040u); /* OBJ on + 1D tiles */
 for(i=0;i<BEAST_PALETTE_ENTRIES;i++)BEAST_OBJ_PALETTE[i]=palette[i];
 for(i=0;i<BEAST_TILE_BYTES/2u;i++)BEAST_OBJ_VRAM[i]=read16(tiles+i*2u);
 return 1;
}
void beast_show(uint8_t frame,uint16_t x,uint16_t y) {
 if(frame>BEAST_CELEBRATING)frame=BEAST_IDLE;
 /* OAM entry 0, square 64x64 4bpp sprite (8x8 tiles x 32 bytes). */
 BEAST_OBJ_OAM[0]=(uint16_t)(y&0xffu); /* attr0 shape square */
 BEAST_OBJ_OAM[1]=(uint16_t)((x&0x1ffu)|(3u<<14)); /* attr1 size 64 */
 BEAST_OBJ_OAM[2]=(uint16_t)(frame*64u); /* attr2 base tile */
}
