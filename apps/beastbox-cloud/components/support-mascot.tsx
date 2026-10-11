'use client';

import { useId } from 'react';
import type { SupportTier } from '../lib/support-tiers';
import ZerefFigure from './zeref-figure';

/** ZEREF the Moonwraith (static CSS-animated rig) with cosmetic support props. No game state. */
export default function SupportMascot({ tier, reacting = false }: { tier?: SupportTier; reacting?: boolean }) {
  const id = useId().replace(/:/g, '');
  const form = tier?.mascot.form ?? 'spark';
  const accent = tier?.mascot.accent ?? '#bca4ff';
  const glow = tier?.mascot.glow ?? '#79dfff';
  const ring = form === 'builder' || form === 'patron';
  const winged = form === 'keeper' || form === 'launch';
  return (
    <svg className={`support-mascot zeref-support form-${form} ${winged ? 'is-winged' : ''} ${reacting ? 'is-reacting' : ''}`}
      viewBox="0 0 400 400" fill="none" aria-hidden="true" focusable="false">
      <ellipse cx="200" cy="361" rx="112" ry="13" fill={accent} opacity=".12"/>
      <g className="support-mascot-orbit" style={{ transformOrigin: '200px 210px' }}>
        {ring && <><ellipse cx="200" cy="210" rx="159" ry="105" stroke={accent} strokeWidth="3" opacity=".65" transform="rotate(-22 200 210)"/>
          {[ [49,174], [324,130], [345,248], [82,303] ].map(([x,y],i) => <circle key={i} cx={x} cy={y} r={form === 'patron' ? 5 : 8} fill={accent}/>)} </>}
      </g>
      {form === 'patron' && <g stroke={accent} strokeWidth="2" opacity=".7"><path d="M72 92 118 51 200 32 292 60 329 99"/>
        {[ [72,92], [118,51], [200,32], [292,60], [329,99] ].map(([x,y],i) => <circle key={i} cx={x} cy={y} r="4" fill={accent}/>)}</g>}
      {form === 'builder' && <g className="support-blueprint" stroke={accent} strokeWidth="2" opacity=".65"><path d="M292 277h67v53h-67zM302 288h47M302 300h24M302 315h39M326 279v49"/><circle cx="310" cy="309" r="5"/></g>}
      {form === 'compute' && <g className="support-charge" stroke={accent} strokeWidth="5" strokeLinejoin="round"><path d="m61 151-19 34h23l-15 29M346 156l-18 29h23l-13 27"/><rect x="299" y="274" width="47" height="66" rx="9" fill="#182943"/><path d="M314 271h18M313 292h19M313 305h19M313 318h19"/></g>}
      {form === 'launch' && <g><path className="support-ignition" d="M174 324q-31 40 26 65 54-26 24-65" fill={accent} opacity=".55"/>
        <path d="M74 348h253l24 20H49z" fill="#35304b" stroke={accent} strokeWidth="3"/>
        {[0,1,2].map(i=><circle className="support-launch-light" key={i} cx={165+i*35} cy="359" r="4" fill={accent} style={{animationDelay:`${i*.6}s`}}/>)}</g>}
      {/* ZEREF the Moonwraith replaces the old petal puff; tier props stay layered around him. */}
      <ZerefFigure id={`${id}-zeref`} accent={accent} glow={glow} css/>
      {form === 'hardware' && <g stroke="#f7d3a0" strokeWidth="5"><rect x="118" y="150" width="76" height="52" rx="15" fill="#111e39" fillOpacity=".4"/><rect x="206" y="150" width="76" height="52" rx="15" fill="#111e39" fillOpacity=".4"/><path d="M194 168h12M118 164l-18-7M282 164l18-7"/></g>}
      {form === 'snack' && <g className="support-snack"><path d="M129 325h142l-14 33H143z" fill="#58416f" stroke={accent} strokeWidth="3"/>
        <ellipse cx="200" cy="325" rx="71" ry="10" fill="#241c3c" stroke={accent} strokeWidth="3"/><path d="m200 297 7 12 14 2-10 10 2 14-13-7-13 7 2-14-10-10 14-2z" fill="#ffdf8f"/></g>}
      {form === 'hardware' && <g className="support-rune" stroke={accent} strokeWidth="3"><rect x="285" y="294" width="46" height="40" rx="4" fill="#19263d"/><path d="M297 290v-7m12 7v-7m12 7v-7M297 336v7m12-7v7m12-7v7M297 305h22v18h-22z"/><path d="m73 328 26-27 8 9-26 27z" fill="#789dad"/></g>}
      <g className="support-reaction-spark" fill={accent}><path d="m62 98 4 11 11 4-11 4-4 11-4-11-11-4 11-4zm272 3 3 9 9 3-9 3-3 9-3-9-9-3 9-3z"/></g>
    </svg>
  );
}
