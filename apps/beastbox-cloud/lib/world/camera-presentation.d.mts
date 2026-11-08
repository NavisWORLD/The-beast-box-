export const CAMERA_SWITCH_ORDER:readonly ['orbit','behind','first'];
export type CamVec={x:number;y:number;z:number};
export type CamPose={mode:string;position:CamVec;up:CamVec;lookAt:CamVec};
export type CamRead={
 traveler?:{n?:CamVec;f?:CamVec;position?:CamVec};
 beast?:{n?:CamVec;f?:CamVec;position?:CamVec};
 radius?:number;
 ground?:number;
};
export function presentationCamera(mode:string|null|undefined,read:CamRead):CamPose|null;
export function stepPresentationCamera(prev:CamPose|null|undefined,pose:CamPose|null|undefined,opts?:{reduced?:boolean;alpha?:number}):CamPose|null;
