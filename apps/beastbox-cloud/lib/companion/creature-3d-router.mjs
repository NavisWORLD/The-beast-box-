/**
 * CREATURE 3D ROUTER — identity-to-renderer binding for dimensional views.
 *
 * Pure module: maps a canonical creature identity to the renderer kind that
 * should draw it in 3D-capable surfaces. It never changes which renderer a
 * page uses by itself; call sites opt in explicitly.
 *
 * Kinds:
 * - zeref-true3d:      the Moonwraith/Zeref dimensional mesh (ZerefTrue3D).
 * - procedural-cosmic: the existing generic Cursor-era rig (CosmicCompanion3D).
 * - sprite-only:       saved QBEASTs keep their recorded-seed sprite path.
 *
 * Identity rule: bb-7f9c2a03 is the Moonwraith display persona and
 * bb-deada969 is the saved Zeref QBEAST. Both resolve to the Zeref mesh
 * family, but the returned qbeastId always preserves the caller's exact
 * identity — the router never merges them.
 */

export const ZEREF_TRUE3D_IDS=Object.freeze(['bb-7f9c2a03','bb-deada969']);
export const RENDERER_KINDS=Object.freeze(['zeref-true3d','procedural-cosmic','sprite-only']);

export function resolveCreature3D({id=null,genome=null,profile=null}={}){
 const qbeastId=typeof id==='string'&&id.length>0?id:(typeof profile?.id==='string'?profile.id:null);
 if(qbeastId&&ZEREF_TRUE3D_IDS.includes(qbeastId))return {kind:'zeref-true3d',qbeastId,reason:'zeref-identity-mesh'};
 const seed=genome?.seed||profile?.genome?.seed||null;
 if(typeof seed==='string'&&seed.length>0)return {kind:'sprite-only',qbeastId,reason:'recorded-seed-sprite'};
 return {kind:'procedural-cosmic',qbeastId,reason:'workshop-profile-rig'};
}
