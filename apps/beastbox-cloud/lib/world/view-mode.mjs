// The world view switch (Cory, Oct 30 2026: perspective as an option). One chip cycles the three views; the choice is remembered per device.
// 'first' is today's default (first-person eye at 1.6 m when you walk), so nothing changes until someone taps the chip.
import {midSentenceName} from './cage-creature.mjs';
export const VIEW_MODES=Object.freeze(['first','behind','orbit']);
export const VIEW_MODE_KEY='beastbox.world.view.v1';
export const VIEW_MODE_EVENT='beastbox:world-view';
export const DEFAULT_VIEW_MODE='first';
export function readViewMode(storage){try{const v=storage?.getItem(VIEW_MODE_KEY);return VIEW_MODES.includes(v)?v:DEFAULT_VIEW_MODE;}catch{return DEFAULT_VIEW_MODE;}}
export function writeViewMode(storage,m){const v=VIEW_MODES.includes(m)?m:DEFAULT_VIEW_MODE;try{storage?.setItem(VIEW_MODE_KEY,v);}catch{}return v;}
export function nextViewMode(m){return VIEW_MODES[(VIEW_MODES.indexOf(m)+1)%VIEW_MODES.length];}
export function viewModeLabel(m,name){const n=midSentenceName(String(name||'').trim()||'Your beast');return m==='behind'?`View: Behind ${n}`:m==='orbit'?'View: Orbit':'View: First person';}
/** Camera wishes for the world loop: eye = use the 1.6 m first-person eye; forceOrbit = hold the orbit zoom. */
export function viewModeCamera(m){return {eye:m==='first',forceOrbit:m==='orbit'};}
