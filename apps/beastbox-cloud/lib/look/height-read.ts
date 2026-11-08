// Read-only adapter over the existing seeded height. This file does not reimplement it.
import {terrainHeightAt} from '../universe/one-world-look.ts';

export type HeightOpts={org:number[];seed:number[];bay:number[];on:boolean;r:number};

export function readSeededHeight(x:number,z:number,opts:HeightOpts){
 return terrainHeightAt(x,z,opts);
}
