// Seeded streams (Oct 23 2026): replaces Math.random everywhere in the app.
// Seed = FNV-1a(label) mixed with the recorded IBM ibm_marrakesh shard digest
// (job db4te7slf4us73c3888g, recorded counts; never re-run). Deterministic per label.
export const RECORDED_SEED_DIGEST='b6a607eaa2c280862deb047fda827de3';
export function seedFrom(label){let h=0x811c9dc5;const s=RECORDED_SEED_DIGEST+':'+String(label);for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}
/** mulberry32 stream in [0,1). */
export function seededStream(label){let a=seedFrom(label);return ()=>{a=(a+0x6D2B79F5)|0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
