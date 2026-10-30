// One sun for every view (living world, pocket, universe). DATA from Cosmo's One Universe look pack v1 (oneworld.json).
// Labels: the sun's direction/colour and the sky stops are SEEDED (designed); the blend and the day-clock height are DERIVED.
// Pure: no three, no DOM, no random calls. The caller passes the time in seconds.
export const ONE_SUN=Object.freeze({label:'SEEDED',dir:[0.5779, 0.5154, -0.6328],azimuthDeg:137.6002,elevationDeg:31.0217,hex:'#FFF0DB',linear:[1.0, 0.875, 0.7055],intensity:3.0283,ambientHex:'#545256',ambient:0.1817});
export const COMPANION_DISC=Object.freeze({label:'SEEDED',hex:'#FFB37A',lights:false,note:'kept as a dim disc with no light, pending Cory'});
export const SKY_STOPS=Object.freeze([{"name": "night", "elev": -18.0, "zenith": [0.0012, 0.0018, 0.0047], "horizon": [0.0021, 0.0031, 0.0081], "star": 1.0}, {"name": "blue_hour", "elev": -8.0, "zenith": [0.0034, 0.0053, 0.03], "horizon": [0.0233, 0.0161, 0.0617], "star": 0.7}, {"name": "dusk", "elev": -2.0, "zenith": [0.0115, 0.0184, 0.0798], "horizon": [0.5798, 0.1447, 0.0687], "star": 0.25}, {"name": "golden", "elev": 4.0, "zenith": [0.0419, 0.1013, 0.2848], "horizon": [0.8906, 0.4466, 0.1952], "star": 0.0}, {"name": "day_low", "elev": 15.0, "zenith": [0.0476, 0.2095, 0.5702], "horizon": [0.5237, 0.6831, 0.8271], "star": 0.0}, {"name": "day_high", "elev": 45.0, "zenith": [0.0287, 0.1894, 0.636], "horizon": [0.6301, 0.7757, 0.8966], "star": 0.0}, {"name": "noon", "elev": 90.0, "zenith": [0.023, 0.1608, 0.5994], "horizon": [0.6538, 0.8027, 0.9177], "star": 0.0}]);
export const HAZE=Object.freeze({airDensity:0.85,fogFarM:1058.8235,label:'DERIVED'});
export const FP_GROUND_EYE_M=1.6;
export const DAY_S=240; // the existing living-world day clock (seconds per day)
const ss=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/** Day phase in [0,1) from wall-clock seconds (plus an optional offset). */
export const dayPhase=(sec,off=0)=>((((sec+off)%DAY_S)+DAY_S)%DAY_S)/DAY_S;
/** Sun height follows the day clock: about 62% of each day is daylight, peak 64 degrees. DERIVED. */
export const sunElevationDeg=phase=>52*Math.sin(2*Math.PI*phase)+12;
/** World direction to the sun for an observer whose local up is `up` (unit [x,y,z]); azimuth from the pack. */
export function localSunDir(up,elevDeg,azDeg=ONE_SUN.azimuthDeg){
 const u=up;let ref=Math.abs(u[1])<.95?[0,1,0]:[1,0,0];
 const d=ref[0]*u[0]+ref[1]*u[1]+ref[2]*u[2];let e=[ref[0]-d*u[0],ref[1]-d*u[1],ref[2]-d*u[2]];const el=Math.hypot(...e)||1;e=e.map(x=>x/el);
 const n=[u[1]*e[2]-u[2]*e[1],u[2]*e[0]-u[0]*e[2],u[0]*e[1]-u[1]*e[0]];
 const a=azDeg*Math.PI/180,h=elevDeg*Math.PI/180,c=Math.cos(h);
 const v=[0,1,2].map(i=>u[i]*Math.sin(h)+c*(Math.cos(a)*e[i]+Math.sin(a)*n[i]));const l=Math.hypot(...v)||1;return v.map(x=>x/l);
}
/** Sky at a sun elevation: smoothstep between neighbouring stops in linear light. Stars are 0 in daylight. */
export function skyAtElevation(elevDeg){
 const s=SKY_STOPS;if(elevDeg<=s[0].elev)return {zenith:[...s[0].zenith],horizon:[...s[0].horizon],starAlpha:s[0].star,stop:s[0].name};
 for(let i=0;i<s.length-1;i++){const a=s[i],b=s[i+1];if(elevDeg<=b.elev){const t=ss(a.elev,b.elev,elevDeg);const m=(x,y)=>x.map((v,k)=>v+(y[k]-v)*t);return {zenith:m(a.zenith,b.zenith),horizon:m(a.horizon,b.horizon),starAlpha:elevDeg>0?0:a.star+(b.star-a.star)*t,stop:t<.5?a.name:b.name};}}
 const z=s[s.length-1];return {zenith:[...z.zenith],horizon:[...z.horizon],starAlpha:0,stop:z.name};
}
/** Phase word for Emeth's sky lines (dawn/day/dusk/night). */
export function skyMoment(elevDeg,rising){if(elevDeg<-4)return 'night';if(elevDeg<10)return rising?'dawn':'dusk';return 'day';}
export const SKY_LINES=Object.freeze({dawn:"First light over {beast}'s land",day:'One sun over every world',dusk:'{beast} watches the light fall',night:'Same sky, now full of stars'});
/** Everything a view needs at time `sec` for local up `up`. */
export function oneSunAt(sec,up=[0,1,0],off=0){const p=dayPhase(sec,off);const e=sunElevationDeg(p);const rising=Math.cos(2*Math.PI*p)>0;
 return {label:'SEEDED',phase:p,elevationDeg:e,dir:localSunDir(up,e),sky:skyAtElevation(e),moment:skyMoment(e,rising),day:ss(-6,8,e)};}
