export type GameChatBridge={token:string;key:string;canGuide:boolean;observeGame?:()=>Promise<any|null>;applyGameAction?:(button:string,expectedKey:string)=>Promise<boolean>};
