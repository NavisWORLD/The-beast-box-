'use client';
import {useEffect,useRef} from 'react';
import {blit,renderBeast,SPRITE} from '../public/spark/draw.mjs';
/** A saved beast's own pixel sprite, drawn from its saved genome (the same renderer the Cage uses). */
export default function CreationThumb({genome,size=30,label}:{genome:any;size?:number;label:string}){
 const ref=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{const c=ref.current;if(!c||!genome)return;const ctx=c.getContext('2d');if(!ctx)return;try{blit(ctx,renderBeast(genome,Number(genome.stage)||2,'open'),0,0,c.width/SPRITE);}catch{}},[genome,size]);
 return <canvas ref={ref} width={SPRITE*2} height={SPRITE*2} role="img" aria-label={label} style={{width:size,height:size,imageRendering:'pixelated'}}/>;}
