import test from 'node:test';import assert from 'node:assert/strict';
import {VOLCANO_DAY_LOOK,VOLCANO_DAY_BODY_MIX_K} from '../lib/universe/fp-volcano-sky.mjs';
test('#740 day body mix 0.45 is kept as a named tuning handle',()=>{assert.equal(VOLCANO_DAY_BODY_MIX_K,.45);assert.equal(VOLCANO_DAY_LOOK.dayBodyK,VOLCANO_DAY_BODY_MIX_K);});
