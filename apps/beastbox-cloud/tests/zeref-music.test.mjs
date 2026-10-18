import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {songOnMind,musicBpm,musicMood,musicLine} from '../lib/companion/zeref-music.mjs';
import {HEART_FALLBACK} from '../lib/companion/zeref-heart.mjs';
const music=JSON.parse(readFileSync(new URL('../public/spark/zeref-music.json',import.meta.url),'utf8'));
test('Cory music memory is features only and wires heart + mood',()=>{
 assert.equal(music.creature_id,'bb-deada969');assert.equal(music.songs.length,5);
 for(const s of music.songs){assert.match(s.audio_sha256,/^[0-9a-f]{64}$/);assert.ok(!('lyrics' in s)&&!('transcript' in s));
  const b=musicBpm(HEART_FALLBACK,s);assert.ok(b>=60&&b<=110);assert.ok(musicMood(s));assert.ok(musicLine(s).includes(s.title));}
 assert.equal(songOnMind(music,0).slug,music.songs[0].slug);assert.equal(songOnMind(music,3600000).slug,music.songs[1].slug);
 assert.equal(musicBpm(HEART_FALLBACK,null),72.29);
});
