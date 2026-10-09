/** Read-only presentation: a Beast's stored care state, not a claim of autonomy. */
export function visualStateFromBeast(beast){
 if(!beast)return 'idle';
 const energy=Number(beast.energy);
 if(Number.isFinite(energy)&&energy<=10)return 'sleeping';
 const recent=!beast.behavior||beast.behavior.tick-(beast.behavior.lastFeedback?.tick??-999)>=0&&beast.behavior.tick-(beast.behavior.lastFeedback?.tick??-999)<=1;
 const mood=['happy','sleep','evolve'].includes(beast.mood)&&!recent?'idle':beast.mood;
 switch(mood){
  case 'sleep':return 'sleeping';
  case 'evolve':
  case 'happy':return 'celebrating';
  case 'listening':return 'listening';
  case 'thinking':return 'thinking';
  case 'halted':return 'halted';
  default:
   // Reflect computational actions only when no explicit care/speech mood overrides them.
   switch(beast.behavior?.lastAction){
    case 'rest': return 'sleeping';
    case 'listen': return 'listening';
    case 'inspect':
    case 'explore': return beast.behavior.events?.at(-1)?.input?.associations?.length?'remembering':'thinking';
    case 'play': return 'celebrating';
    case 'wander': return 'observing';
    default: return 'idle';
   }
 }
}
