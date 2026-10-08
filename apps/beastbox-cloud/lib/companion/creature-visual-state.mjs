/** Read-only presentation: a Beast's stored care state, not a claim of autonomy. */
export function visualStateFromBeast(beast){
 if(!beast)return 'idle';
 const energy=Number(beast.energy);
 if(Number.isFinite(energy)&&energy<=10)return 'sleeping';
 switch(beast.mood){
  case 'sleep':return 'sleeping';
  case 'evolve':
  case 'happy':return 'celebrating';
  case 'listening':return 'listening';
  case 'thinking':return 'thinking';
  case 'halted':return 'halted';
  default:return 'idle';
 }
}
