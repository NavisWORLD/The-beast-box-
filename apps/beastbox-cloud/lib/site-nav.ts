// ONE site menu (Oct 16 2026): every page gets the same grouped areas through <SiteNav/> in the root layout.
export type NavItem={label:string;href:string;icon:string;note?:string};
export type NavGroup={key:string;label:string;items:NavItem[]};
export const SITE_NAV:readonly NavGroup[]=[
 {key:'home',label:'Home',items:[{label:'Home',href:'/',icon:'🏠'}]},
 {key:'zeref',label:'Zeref',items:[{label:'Talk to Zeref',href:'/beast-cage/talk',icon:'🌙'},{label:'Zeref’s diary',href:'/beast-cage#zeref-diary',icon:'📔'}]},
 {key:'cage',label:'Beast Cage',items:[{label:'Pocket cage',href:'/beast-cage',icon:'🏰'},{label:'Open Field (AR)',href:'/beast-cage/field',icon:'📷'},{label:'Field game',href:'/beast-cage/go',icon:'🧭'},{label:'Play',href:'/beast-cage/play',icon:'🕹️'},{label:'Turntable',href:'/beast-cage/turntable',icon:'🔄'},{label:'Guest cage',href:'/beast-cage/guest',icon:'🐾'}]},
 {key:'game',label:'Lost COSMOS',items:[{label:'Lost COSMOS game',href:'/sol-game',icon:'🎮'}]},
 {key:'spark',label:'Spark',items:[{label:'Spark Lab · my beast',href:'/spark/index.html',icon:'🐣'},{label:'Try it',href:'/try',icon:'✨'}]},
 {key:'brain',label:'Brain Bay',items:[{label:'Brain Bay',href:'/brain-bay',icon:'🧠'}]},
 {key:'research',label:'Research & evidence',items:[{label:'Research lab',href:'/research',icon:'🔬'},{label:'Stage 015 receipts',href:'/research/stage015',icon:'🧾'},{label:'What’s next',href:'/next',icon:'🛰️'}]},
 {key:'account',label:'Account',items:[{label:'Account',href:'/account',icon:'👤'},{label:'Settings',href:'/settings',icon:'⚙️'},{label:'Muse headband',href:'/connect/meta-muse',icon:'🎧'},{label:'Privacy',href:'/privacy',icon:'🔒'}]},
 {key:'workshop',label:'Workshop',items:[{label:'Workshop (owner unlock)',href:'/workspace',icon:'🛠️',note:'owner only'}]},
];
export const SITE_NAV_HREFS=SITE_NAV.flatMap(g=>g.items.map(i=>i.href));
