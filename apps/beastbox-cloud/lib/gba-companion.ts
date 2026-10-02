/**
 * BEAST CAGE GBA v1. Public export is a portable character/animation module,
 * never an LLM, living organism, credential, private memory, or permission grant.
 * Only an explicit owner click may include validated measured dyn12 samples.
 */
import {FAMILIES,STAT_NAMES,validCreature,type CreatureProfile} from './creature-profile';
export type Look='nebula'|'aurora'|'starlight';
export type Mood='idle'|'listening'|'thinking'|'celebrating';
export type Measured={sequence:number;checkpoint:string;cns:number[];synaptic:number[]};
export const GBA_EXPORT_SCHEMA='beast-cage-gba-v1' as const;
const LOOKS:Look[]=['nebula','aurora','starlight'];
const MOODS:Mood[]=['idle','listening','thinking','celebrating'];
// Index zero is OBJ-transparent. Every pixel uses one of only sixteen colors.
const PALETTES:Record<Look,number[]>={
 nebula:[0x000000,0x17163b,0x35246b,0x58429b,0x8563c7,0xab86e4,0xd6b6fa,0xffdcfa,0x81d9ff,0xff9ed5,0xffd87d,0xffffff,0x3e3072,0xbad9ff,0xf5efff,0x7265ad],
 aurora:[0x000000,0x111e35,0x23475a,0x317f93,0x55b9c0,0x79d5dd,0xb3f4eb,0xe5fffa,0x9abaff,0xffc1eb,0xffd87d,0xffffff,0x356b7f,0xc7e8ff,0xf6ffff,0x5788a9],
 starlight:[0x000000,0x281c40,0x4e3567,0x8360a1,0xae89d0,0xd8b4ed,0xf0d8fa,0xffebff,0xb2e7ff,0xffb0d9,0xffd87d,0xffffff,0x71518f,0xe1d4ff,0xffffff,0x9c7eba]
};
export function validLook(value:unknown):value is Look{return typeof value==='string'&&LOOKS.includes(value as Look);}
function colorComponents(color:number){return [(color>>>16)&255,(color>>>8)&255,color&255];}
export function paletteBytes(look:Look):Uint8Array{
 const result=new Uint8Array(32);
 PALETTES[look].forEach((color,i)=>{
  const [r,g,b]=colorComponents(color);
  const bgr=((r>>3)|((g>>3)<<5)|((b>>3)<<10));
  result[i*2]=bgr&255;result[i*2+1]=(bgr>>>8)&255;
 });
 return result;
}
export function framePixels(look:Look,mood:Mood):Uint8Array{
 // Deterministic, editable 64x64 reinterpretation of Cory's galaxy design.
 // No random animation or fake runtime telemetry is baked into the artwork.
 const p=new Uint8Array(64*64);
 const mark=(x:number,y:number,c:number)=>{if(x>=0&&x<64&&y>=0&&y<64)p[y*64+x]=c;};
 const ellipse=(x0:number,y0:number,rx:number,ry:number,c:number)=>{
  for(let y=Math.max(0,Math.floor(y0-ry));y<=Math.min(63,Math.ceil(y0+ry));y++)
   for(let x=Math.max(0,Math.floor(x0-rx));x<=Math.min(63,Math.ceil(x0+rx));x++){
    const d=((x-x0)/rx)**2+((y-y0)/ry)**2;if(d<=1)mark(x,y,c);
   }
 };
 const fins=mood==='listening'?15:mood==='celebrating'?18:13;
 for(let i=0;i<11;i++){
  const angle=(i/11)*Math.PI*2;
  const fx=32+Math.cos(angle)*fins,fy=35+Math.sin(angle)*fins*.88;
  ellipse(fx,fy,7+(i%2),8+(i%3),8);
  ellipse(fx-1,fy-1,4,5,5);
 }
 const squash=mood==='thinking'?1:mood==='celebrating'?-1:0;
 ellipse(32,35,21,19+squash,1);
 ellipse(32,34,20,18+squash,3);
 ellipse(30,31,17,15,4);
 ellipse(28,28,12,10,5);
 ellipse(27,27,9,7,6);
 // Hand-placed nebula constellations: clearly fictional texture.
 for(let i=0;i<32;i++){
  const x=14+(i*19+i*i*3)%35,y=19+(i*11+i*i)%35;
  const d=((x-32)/20)**2+((y-35)/18)**2;
  if(d<.88&&p[y*64+x]!==0)mark(x,y,i%7===0?11:i%3===0?8:6);
 }
 // The original character's star-shaped eyes and mischievous smile.
 for(const ex of [24,40]){
  ellipse(ex,36,5,7,1);ellipse(ex,35,4,6,2);
  mark(ex,32,11);mark(ex,33,10);mark(ex-1,33,10);mark(ex+1,33,10);
  mark(ex,34,10);mark(ex-2,31,11);mark(ex+2,38,11);
 }
 ellipse(18,43,3,2,9);ellipse(46,43,3,2,9);
 for(let x=28;x<=36;x++)mark(x,44+Math.floor(Math.abs(x-32)*-.36),1);
 for(let x=30;x<=34;x++)mark(x,46,9);
 // Halo is intentionally above the silhouette (not a generic sphere).
 const sy=mood==='celebrating'?3:6;
 for(let y=-5;y<=5;y++)for(let x=-5;x<=5;x++){
  if(Math.abs(x)+Math.abs(y)*.6<=5&&(Math.abs(x)<=1||Math.abs(y)<=1||Math.abs(x)+Math.abs(y)<5))
   mark(32+x,sy+y,10);
 }
 mark(32,sy,11);mark(22,sy+3,10);mark(42,sy+3,10);
 return p;
}
export function spriteTiles(look:Look):Uint8Array{
 const bytes=new Uint8Array(4*2048);
 MOODS.forEach((mood,frame)=>{
  const px=framePixels(look,mood);
  for(let tileY=0;tileY<8;tileY++)for(let tileX=0;tileX<8;tileX++){
   const tile=(tileY*8+tileX)*32+frame*2048;
   for(let y=0;y<8;y++)for(let x=0;x<8;x+=2){
    const pos=(tileY*8+y)*64+tileX*8+x;
    bytes[tile+y*4+x/2]=px[pos]|(px[pos+1]<<4);
   }
  }
 });
 return bytes;
}
export function spritePreview(look:Look,mood:Mood,canvas:HTMLCanvasElement):void{
 const ctx=canvas.getContext('2d');
 if(!ctx)throw Error('Canvas preview unavailable');
 canvas.width=64;canvas.height=64;
 const pic=ctx.createImageData(64,64),indices=framePixels(look,mood);
 for(let i=0;i<indices.length;i++){
  const c=indices[i],at=i*4,parts=colorComponents(PALETTES[look][c]);
  pic.data[at]=parts[0];pic.data[at+1]=parts[1];pic.data[at+2]=parts[2];pic.data[at+3]=c?255:0;
 }
 ctx.putImageData(pic,0,0);
}
function vector(value:unknown):value is number[]{
 return Array.isArray(value)&&value.length===12&&value.every(x=>typeof x==='number'&&Number.isFinite(x)&&x>=-127.996&&x<=127.996);
}
export function latestMeasured(trace:Record<string,unknown>[]):Measured|null{
 for(let i=trace.length-1;i>=0;i--){
  const event=trace[i],signals=event.signals as Record<string,unknown>|undefined;
  if(!signals||signals.schema!=='substrate-signal-v1'||signals.provenance!=='measured-during-durable-turn')continue;
  const dims=signals.dyn12 as Record<string,unknown>|undefined;
  if(!dims||!vector(dims.cns_after)||!vector(dims.synaptic_after))continue;
  const sequence=event.sequence,checksum=event.checkpoint_sha256;
  if(!Number.isSafeInteger(sequence)||Number(sequence)<0||typeof checksum!=='string'||!/^[a-f0-9]{64}$/i.test(checksum))continue;
  return {sequence:Number(sequence),checkpoint:checksum,cns:[...dims.cns_after],synaptic:[...dims.synaptic_after]};
 }
 return null;
}
function q8(value:number):number{
 const scaled=Math.round(value*256);
 if(scaled<-32768||scaled>32767)throw Error('Signal outside portable Q8.8 range; no silent saturation');
 return scaled;
}
export function stateBytes(look:Look,measured:Measured|null):Uint8Array{
 const raw=new Uint8Array(60),view=new DataView(raw.buffer);
 raw.set([66,67,71,49],0);raw[4]=1;raw[5]=LOOKS.indexOf(look);raw[6]=measured?1:0;raw[7]=0;
 view.setUint32(8,measured?.sequence??0,true);
 const all=measured?[...measured.cns,...measured.synaptic]:Array(24).fill(0);
 for(let i=0;i<24;i++)view.setInt16(12+i*2,q8(all[i]),true);
 return raw;
}
export function soulManifest(look:Look,measured:Measured|null){
 return {
  schema:GBA_EXPORT_SCHEMA,character:'cosmic-galaxy-creature',creator:'Cory Davis / NavisWORLD',
  visual_look:look,look_id:LOOKS.indexOf(look),sprites:{size:[64,64],format:'GBA-4bpp-8x8-tile-order',frames:MOODS,palette:'GBA-BGR555',tile_bytes:8192},
  signals:{
   provenance:measured?'authenticated checkpoint-backed owner trace':'user-selected visual preset only',
   measured:!!measured,checkpoint_sequence:measured?.sequence??null,checkpoint_sha256:measured?.checkpoint??null,
   cns_dyn12:measured?.cns??null,synaptic_dyn12:measured?.synaptic??null,
   encoding:'signed int16 Q8.8 for GBA; missing telemetry zero-filled and flagged NOT measured'
  },
  includes_personal_memories:false,model_weights_included:false,tool_authority:false,hardware_measurements_included:false,
  note:'Portable character + verified optional numeric snapshot; not a consciousness, model, or live brain transfer.'
 };
}
function crc32(content:Uint8Array):number{
 let c=0xffffffff;
 for(const byte of content){c^=byte;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}
 return (c^0xffffffff)>>>0;
}
function zipStore(files:{name:string;bytes:Uint8Array}[]):Uint8Array{
 const enc=new TextEncoder(),locals:Uint8Array[]=[],directory:Uint8Array[]=[];
 let offset=0;
 for(const file of files){
  const name=enc.encode(file.name);
  if(name.length>65535||file.bytes.length>1_000_000)throw Error('Invalid pack entry');
  const checksum=crc32(file.bytes),local=new Uint8Array(30+name.length),lv=new DataView(local.buffer);
  lv.setUint32(0,0x04034b50,true);lv.setUint16(4,20,true);
  lv.setUint16(6,0x800,true);lv.setUint16(8,0,true);lv.setUint32(14,checksum,true);
  lv.setUint32(18,file.bytes.length,true);lv.setUint32(22,file.bytes.length,true);
  lv.setUint16(26,name.length,true);local.set(name,30);
  locals.push(local,file.bytes);
  const central=new Uint8Array(46+name.length),dv=new DataView(central.buffer);
  dv.setUint32(0,0x02014b50,true);dv.setUint16(4,20,true);dv.setUint16(6,20,true);
  dv.setUint16(8,0x800,true);dv.setUint32(16,checksum,true);
  dv.setUint32(20,file.bytes.length,true);dv.setUint32(24,file.bytes.length,true);
  dv.setUint16(28,name.length,true);dv.setUint32(42,offset,true);central.set(name,46);
  directory.push(central);offset+=local.length+file.bytes.length;
 }
 const size=directory.reduce((sum,v)=>sum+v.length,0),footer=new Uint8Array(22),dv=new DataView(footer.buffer);
 dv.setUint32(0,0x06054b50,true);dv.setUint16(8,files.length,true);dv.setUint16(10,files.length,true);
 dv.setUint32(12,size,true);dv.setUint32(16,offset,true);
 const all=[...locals,...directory,footer],output=new Uint8Array(all.reduce((sum,v)=>sum+v.length,0));
 let at=0;for(const item of all){output.set(item,at);at+=item.length;}return output;
}
function sourceHeader(tiles:Uint8Array,palette:Uint8Array):string{
 const toC=(input:Uint8Array,type:string)=>'static const '+type+' '+(type==='unsigned short'?'beast_palette':'beast_tiles')+'[] = {\n'+
  Array.from(input).reduce<string[]>((rows,x,i)=>{if(i%16===0)rows.push('');rows[rows.length-1]+='0x'+x.toString(16).padStart(2,'0')+', ';return rows;},[]).join('\n')+'\n};\n';
 const palette16=new Uint8Array(32);palette16.set(palette);
 let text='#ifndef BEAST_CAGE_ASSETS_H\n#define BEAST_CAGE_ASSETS_H\n/* Generated 64x64 4bpp x 4 frames. GBA sprite-only, no owner data. */\n';
 text+=toC(tiles,'unsigned char');
 text+='static const unsigned short beast_palette[] = {\n';
 for(let i=0;i<32;i+=2)text+='0x'+(palette16[i]|palette16[i+1]<<8).toString(16).padStart(4,'0')+', ';
 return text+'\n};\n#endif\n';
}
/** v1 extension. The old 60-byte BCG1 signal format remains unchanged. */
function hueRotate(color:number,angle:number):number{
 const r=((color>>>16)&255)/255,g=((color>>>8)&255)/255,b=(color&255)/255;
 const max=Math.max(r,g,b),min=Math.min(r,g,b),delta=max-min;
 let h=0,s=0;const l=(max+min)/2;
 if(delta>0){
  s=delta/(1-Math.abs(2*l-1));
  if(max===r)h=((g-b)/delta)%6;
  else if(max===g)h=(b-r)/delta+2;
  else h=(r-g)/delta+4;
  h*=60;
 }
 h=((h+angle)%360+360)%360;
 const c=(1-Math.abs(2*l-1))*s,x=c*(1-Math.abs((h/60)%2-1)),m=l-c/2;
 let nr=0,ng=0,nb=0;
 if(h<60){nr=c;ng=x;}else if(h<120){nr=x;ng=c;}
 else if(h<180){ng=c;nb=x;}else if(h<240){ng=x;nb=c;}
 else if(h<300){nr=x;nb=c;}else{nr=c;nb=x;}
 const channel=(v:number)=>Math.min(255,Math.max(0,Math.round((v+m)*255)));
 return (channel(nr)<<16)|(channel(ng)<<8)|channel(nb);
}
export function profilePaletteBytes(profile:CreatureProfile):Uint8Array{
 if(!validCreature(profile))throw Error('Invalid generated game character');
 const colors=PALETTES[profile.baseLook].map((color,i)=>i===0?color:hueRotate(color,profile.appearance.hueShift));
 const output=new Uint8Array(32);
 colors.forEach((color,i)=>{
  const [r,g,b]=colorComponents(color),bgr=(r>>3)|((g>>3)<<5)|((b>>3)<<10);
  output[i*2]=bgr&255;output[i*2+1]=bgr>>>8;
 });
 return output;
}
export function profileFramePixels(profile:CreatureProfile,mood:Mood):Uint8Array{
 if(!validCreature(profile))throw Error('Invalid generated game character');
 const out=framePixels(profile.baseLook,mood);
 // Distinct seeded galaxy highlights within the existing original silhouette.
 let n=profile.appearance.constellation;
 for(let i=0;i<9;i++){
  n=(Math.imul(n,1664525)+1013904223)>>>0;
  const x=19+n%27,y=24+((n>>>11)%22),at=y*64+x;
  if(out[at]>0&&out[at]<9)out[at]=i%3===0?11:8;
 }
 return out;
}
export function profileSpriteTiles(profile:CreatureProfile):Uint8Array{
 const out=new Uint8Array(8192);
 MOODS.forEach((mood,frame)=>{
  const pixels=profileFramePixels(profile,mood);
  for(let ty=0;ty<8;ty++)for(let tx=0;tx<8;tx++){
   const tile=(ty*8+tx)*32+frame*2048;
   for(let y=0;y<8;y++)for(let x=0;x<8;x+=2){
    const pos=(ty*8+y)*64+tx*8+x;
    out[tile+y*4+x/2]=pixels[pos]|(pixels[pos+1]<<4);
   }
  }
 });
 return out;
}
export function profilePreview(profile:CreatureProfile,mood:Mood,canvas:HTMLCanvasElement){
 const ctx=canvas.getContext('2d');if(!ctx)throw Error('Pixel preview unavailable');
 const palette=profilePaletteBytes(profile),pixels=profileFramePixels(profile,mood);
 canvas.width=64;canvas.height=64;
 const image=ctx.createImageData(64,64);
 for(let i=0;i<4096;i++){
  const color=pixels[i],value=palette[color*2]|(palette[color*2+1]<<8),j=i*4;
  image.data[j]=((value&31)*255/31)|0;
  image.data[j+1]=(((value>>5)&31)*255/31)|0;
  image.data[j+2]=(((value>>10)&31)*255/31)|0;
  image.data[j+3]=color===0?0:255;
 }
 ctx.putImageData(image,0,0);
}
/** Compact versioned game data, NEVER an authenticated COSMOS checkpoint. */
export function creatureProfileBytes(profile:CreatureProfile):Uint8Array{
 if(!validCreature(profile))throw Error('Invalid game character');
 const out=new Uint8Array(64),view=new DataView(out.buffer);
 out.set([66,67,80,49]); // BCP1; distinct from legacy BCG1 CNS snapshot
 out[4]=1;out[5]=FAMILIES.indexOf(profile.family);out[6]=LOOKS.indexOf(profile.baseLook);
 STAT_NAMES.forEach((key,i)=>{out[8+i]=profile.game.stats[key];});
 (['curiosity','energy','playfulness','caution','independence'] as const)
  .forEach((key,i)=>{out[18+i]=profile.temperament[key];});
 view.setInt8(23,Math.max(-128,Math.min(127,profile.appearance.hueShift)));
 view.setUint32(24,Number.parseInt(profile.id.slice(3),16),true);
 view.setUint32(60,crc32(out.subarray(0,60)),true);
 return out;
}
function creatureHeader(bytes:Uint8Array):string{
 const lines=['#ifndef BEAST_CAGE_CREATURE_PROFILE_H','#define BEAST_CAGE_CREATURE_PROFILE_H',
  '/* BCP1: purely fictional seeded game statistics; no private owner data. */',
  'static const unsigned char beast_creature_profile[64] = {'];
 for(let i=0;i<64;i+=8)lines.push('  '+Array.from(bytes.slice(i,i+8)).map(x=>'0x'+x.toString(16).padStart(2,'0')).join(', ')+',');
 lines.push('};','#endif','');return lines.join('\n');
}

export async function makeGbaZip(look:Look,measured:Measured|null,profile?:CreatureProfile):Promise<Uint8Array>{
 if(!validLook(look))throw Error('Unsupported visual look');
 if(profile&&(!validCreature(profile)||profile.baseLook!==look))throw Error('Game character and sprite look disagree');
 // No remote provider calls; fetch only fixed public same-origin module source.
 const resources=['beast_companion.h','beast_companion.c','example_gba.c','README.md','AGENTS.md',...(profile?['beast_creature_profile.h','beast_creature_profile.c','GENESIS_PROFILE.md']:[])];
 const entries:{name:string;bytes:Uint8Array}[]=[];
 for(const name of resources){
  const result=await fetch('/gba-module/'+name,{credentials:'omit'});
  if(!result.ok)throw Error('Public GBA module source unavailable: '+name);
  const content=new Uint8Array(await result.arrayBuffer());
  if(content.byteLength>60000)throw Error('Unexpected module source size');
  entries.push({name:'gba/'+name,bytes:content});
 }
 const art=await fetch('/cosmic-creature.svg',{credentials:'omit'});
 if(!art.ok)throw Error('Companion source artwork is unavailable');
 entries.push({name:'art/cosmic-creature.svg',bytes:new Uint8Array(await art.arrayBuffer())});
 const tiles=profile?profileSpriteTiles(profile):spriteTiles(look),palette=profile?profilePaletteBytes(profile):paletteBytes(look),encoder=new TextEncoder(),manifest=soulManifest(look,measured);
 entries.push({name:'gba/companion_tiles.4bpp',bytes:tiles});
 entries.push({name:'gba/companion_palette.bgr555',bytes:palette});
 entries.push({name:'gba/companion_assets.h',bytes:encoder.encode(sourceHeader(tiles,palette))});
 entries.push({name:'gba/companion_state.bin',bytes:stateBytes(look,measured)});
 if(profile){
  const bytes=creatureProfileBytes(profile);
  const safe={schema:profile.schema,version:profile.version,id:profile.id,seed:profile.seed,name:profile.name,
   family:profile.family,baseLook:profile.baseLook,appearance:profile.appearance,
   temperament:profile.temperament,game:profile.game,provenance:profile.provenance};
  entries.push({name:'gba/companion_profile.bin',bytes});
  entries.push({name:'gba/companion_profile.h',bytes:encoder.encode(creatureHeader(bytes))});
  entries.push({name:'companion.profile.json',bytes:encoder.encode(JSON.stringify(safe,null,2)+'\n')});
 }
 entries.push({name:'companion.soul.json',bytes:encoder.encode(JSON.stringify(manifest,null,2)+'\n')});
 entries.push({name:'PROVENANCE.txt',bytes:encoder.encode('Cory Davis / NavisWORLD. Original Beast Cage character source, GBA pixel-art adaptation and explicitly approved optional numeric signals. No model weights or private memory exported.\n')});
 return zipStore(entries);
}
