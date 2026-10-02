#include "beast_creature_profile.h"
#include <stddef.h>
static uint32_t read32le(const uint8_t *p){
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint32_t checksum(const uint8_t *p,uint32_t len){
 uint32_t crc=0xffffffffu;
 uint32_t i,j;
 for(i=0;i<len;i++){
  crc^=(uint32_t)p[i];
  for(j=0;j<8u;j++)crc=(crc>>1)^((crc&1u)?0xedb88320u:0u);
 }
 return crc^0xffffffffu;
}
int beast_decode_game_profile(const uint8_t *p,uint32_t len,beast_game_profile_t *out){
 uint32_t i,total=0u;
 if(p==NULL||out==NULL||len!=BEAST_GAME_PROFILE_BYTES)return 0;
 if(p[0]!='B'||p[1]!='C'||p[2]!='P'||p[3]!='1'||
    p[4]!=1u||p[5]>=7u||p[6]>=3u||p[7]!=0u)return 0;
 if(checksum(p,60u)!=read32le(p+60u))return 0;
 for(i=8u;i<18u;i++){if(p[i]<20u||p[i]>80u)return 0;total+=p[i];}
 if(total!=500u)return 0;
 for(i=18u;i<23u;i++)if(p[i]<20u||p[i]>80u)return 0;
 for(i=28u;i<60u;i++)if(p[i]!=0u)return 0;
 out->family=p[5];out->base_look=p[6];
 for(i=0;i<10u;i++)out->stats[i]=p[8u+i];
 for(i=0;i<5u;i++)out->temperament[i]=p[18u+i];
 out->hue_shift=(int8_t)p[23];out->stable_id_hash=read32le(p+24u);
 return 1;
}
