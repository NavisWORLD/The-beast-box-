#ifndef BEAST_CREATURE_PROFILE_H
#define BEAST_CREATURE_PROFILE_H
#include <stdint.h>
#define BEAST_GAME_PROFILE_BYTES 64u
typedef struct {
 uint8_t family; /* 0..6, fictional game family */
 uint8_t base_look; /* 0..2 */
 uint8_t stats[10]; /* sum exactly 500, each 20..80 */
 uint8_t temperament[5]; /* visual/game preference, not a permission */
 int8_t hue_shift;
 uint32_t stable_id_hash;
} beast_game_profile_t;
/* No filesystem, sensors, tools, allocations, backend or model calls. */
int beast_decode_game_profile(const uint8_t *bytes,uint32_t length,beast_game_profile_t *out);
#endif
