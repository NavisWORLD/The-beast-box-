// ONE site menu (Oct 16 2026): every page gets the same grouped areas through <SiteNav/> in the root layout.
export type NavItem={label:string;href:string;icon:string;note?:string;beast?:'meet'|'look'};
export type NavGroup={key:string;label:string;items:NavItem[]};
// Oct 22 2026 (Emeth's structure): the Cage and home are one living universe. The Cage is your beast's home and tiny world
// (things you do inside it), The Universe is the zoom out to the other worlds (Beach Two is a beach on one of them).
// 'Meet your beast' and 'Look closer' are relabelled with the active beast's real name by <SiteNav/> (beast: true).
export const SITE_NAV:readonly NavGroup[]=[
 {key:'home',label:'Home',items:[{label:'Home',href:'/',icon:'🏠'},{label:'Meet your beast',href:'/spark/index.html',icon:'🐣',beast:'meet'}]},
 {key:'cage',label:'The Cage',items:[{label:'Pocket cage',href:'/beast-cage',icon:'🏰',note:'your beast’s home and tiny world'},{label:'Look closer',href:'/beast-cage/look',icon:'🔍',note:'360° view · or tap a creature in the Cage',beast:'look'},{label:'Adventure walk',href:'/beast-cage/play',icon:'🕹️'},{label:'Field game',href:'/beast-cage/go',icon:'🧭'},{label:'Open Field (AR)',href:'/beast-cage/field',icon:'📷'},{label:'Guest cage',href:'/beast-cage/guest',icon:'🐾'}]},
 {key:'universe',label:'The Universe',items:[{label:'Zoom out to the worlds',href:'/universe',icon:'🌌'},{label:'Beach Two',href:'/beach-two',icon:'🏖️',note:'a beach on a planet'}]},
 {key:'zeref',label:'Zeref',items:[{label:'Talk to Zeref',href:'/beast-cage/talk',icon:'🌙'},{label:'Zeref’s diary',href:'/beast-cage#zeref-diary',icon:'📔'}]},
 {key:'game',label:'Lost COSMOS',items:[{label:'Lost COSMOS game',href:'/sol-game',icon:'🎮'}]},
 {key:'spark',label:'Spark Lab',items:[{label:'Spark Lab · my beast',href:'/spark/index.html',icon:'🧪'},{label:'Try it',href:'/try',icon:'✨'}]},
 {key:'brain',label:'Brain Bay',items:[{label:'Brain Bay',href:'/brain-bay',icon:'🧠'}]},
 {key:'research',label:'Research & evidence',items:[{label:'Research lab',href:'/research',icon:'🔬'},{label:'Stage 015 receipts',href:'/research/stage015',icon:'🧾'},{label:'What’s next',href:'/next',icon:'🛰️'}]},
 {key:'account',label:'Account',items:[{label:'Account',href:'/account',icon:'👤'},{label:'Settings',href:'/settings',icon:'⚙️'},{label:'Muse headband',href:'/connect/meta-muse',icon:'🎧'},{label:'Privacy',href:'/privacy',icon:'🔒'}]},
 {key:'workshop',label:'Workshop',items:[{label:'Workshop (owner unlock)',href:'/workspace',icon:'🛠️',note:'owner only'}]},
];
/** The active beast's real name from the companion save (no hardcoded names); null when none is saved. */
export function activeBeastName(raw:string|null):string|null{try{const v=raw?JSON.parse(raw):null;const n=v?.name||v?.displayName;return typeof n==='string'&&n.trim()?n.trim().slice(0,32):null;}catch{return null;}}
export function navLabel(i:NavItem,name:string|null):string{if(!name||!i.beast)return i.label;return i.beast==='meet'?'Meet '+name:'Look closer at '+name;}
export const SITE_NAV_HREFS=SITE_NAV.flatMap(g=>g.items.map(i=>i.href));
