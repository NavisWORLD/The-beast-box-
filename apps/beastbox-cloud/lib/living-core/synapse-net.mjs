/**
 * Sensor + wire network for living-core creatures, generated from the 12-channel Cosmic Synapse state
 * (CST12 in lib/physics/cst-integrator.mjs). Pure: given the body mesh's vertices/normals it picks
 * golden-angle-spaced sensor nodes just under the surface (one family per CST channel), wires each to
 * its nearest neighbours along the body, and integrates per-channel firing from the channel values.
 */
import {CST12,PHI} from '../physics/cst-integrator.mjs';
export {CST12};
/** nodes: Float32Array xyz, ch: Uint8Array channel per node, edges: Uint16Array pairs. */
export function buildSynapseNet(pos,nrm,count,{perChannel=8,inset=.012,neighbours=2}={}){
 const N=Math.min(CST12.length*perChannel,Math.max(0,count));const nodes=new Float32Array(N*3),ch=new Uint8Array(N);
 const used=new Set();let k=0;
 for(let i=0;k<N&&i<N*8;i++){const v=Math.floor(((i*PHI)%1)*count);if(used.has(v))continue;used.add(v);
  for(let a=0;a<3;a++)nodes[k*3+a]=pos[v*3+a]-(nrm?nrm[v*3+a]*inset:0);ch[k]=k%CST12.length;k++;}
 const edges=[];const n=k;
 for(let i=0;i<n;i++){const d=[];for(let j=0;j<n;j++){if(i===j)continue;const dx=nodes[i*3]-nodes[j*3],dy=nodes[i*3+1]-nodes[j*3+1],dz=nodes[i*3+2]-nodes[j*3+2];d.push([dx*dx+dy*dy+dz*dz,j]);}
  d.sort((a,b)=>a[0]-b[0]);for(let q=0;q<Math.min(neighbours,d.length);q++){const j=d[q][1];if(i<j)edges.push(i,j);else if(!edges.some((_,e)=>e%2===0&&edges[e]===j&&edges[e+1]===i))edges.push(j,i);}}
 return {nodes:nodes.subarray(0,n*3),ch:ch.subarray(0,n),edges:Uint16Array.from(edges),count:n};
}
/** Channel values (0..1) from a CST state's channels (missing ones derived so all 12 exist). */
export function channelValues(S){const c=S?.ch||{};const m={frequency_mass:c.resonance,geometric_phase:((S?.phase||0)/(Math.PI*2))%1,spectral_flatness:1-(c.coherence??.6),phase_velocity:c.chaos,entanglement:c.coherence,valence:c.valence,arousal:c.arousal,dominance:c.dominance,audio_psi:c.audio_psi??.3,phi_harmonics:c.phi_harmonics,av_coherence:c.coherence,quantum_entropy:c.quantum_entropy};
 return CST12.map(k=>{const v=Number(m[k]);return Number.isFinite(v)?Math.min(1,Math.max(0,v)):.5;});}
/** Integrate-and-fire per channel: rate .25..2.4 Hz scaled by excitation (chat/audio/touch/emotion). Returns fired channel ids. */
export function fireStep(acc,vals,dt,excite=0){const out=[];for(let i=0;i<acc.length;i++){acc[i]+=dt*(.25+2.15*vals[i])*(1+2.5*Math.min(1,Math.max(0,excite)));if(acc[i]>=1){acc[i]-=1;out.push(i);}}return out;}
/** Emotion -> excitation + ripple frequency (Hz) for the soft-body vibration layer. */
export const EMO_VIBE=Object.freeze({calm:{ex:.1,hz:1.2},happy:{ex:.5,hz:2.4},curious:{ex:.35,hz:1.8},scared:{ex:.8,hz:4.2},sleepy:{ex:0,hz:.6},angry:{ex:.7,hz:3.4}});
