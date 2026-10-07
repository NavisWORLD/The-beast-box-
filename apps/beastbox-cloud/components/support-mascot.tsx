'use client';

import { useId } from 'react';
import type { SupportTier } from '../lib/support-tiers';

/** The original galaxy/petal Beast, with cosmetic support props. No game state. */
export default function SupportMascot({ tier, reacting = false }: { tier?: SupportTier; reacting?: boolean }) {
  const id = useId().replace(/:/g, '');
  const form = tier?.mascot.form ?? 'spark';
  const accent = tier?.mascot.accent ?? '#bca4ff';
  const glow = tier?.mascot.glow ?? '#79dfff';
  const body = `${id}-body`, eye = `${id}-eye`, petal = `${id}-petal`;
  const ring = form === 'builder' || form === 'patron';
  const winged = form === 'keeper' || form === 'launch';
  return (
    <svg className={`support-mascot form-${form} ${reacting ? 'is-reacting' : ''}`}
      viewBox="0 0 400 400" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={body} cx=".35" cy=".25" r=".8">
          <stop stopColor="#f4eaff"/><stop offset=".34" stopColor={accent}/>
          <stop offset=".66" stopColor="#6952bf"/><stop offset="1" stopColor="#252254"/>
        </radialGradient>
        <linearGradient id={petal} x2="1" y2="1">
          <stop stopColor={glow}/><stop offset=".48" stopColor="#b695ed"/>
          <stop offset="1" stopColor="#604f9c"/>
        </linearGradient>
        <linearGradient id={eye} x2="0" y2="1">
          <stop stopColor="#191835"/><stop offset="1" stopColor="#42376b"/>
        </linearGradient>
      </defs>
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
      <g className="support-mascot-float">
        <g className="support-mascot-tail"><path d="M278 294q75-5 59-72 36 49 5 87-26 27-72 9" fill={`url(#${petal})`} stroke={accent} strokeWidth="2"/></g>
        {winged && <g className="support-mascot-wings" fill={`url(#${petal})`} stroke={accent} strokeWidth="2"><path d="M119 235q-56-70-93-39l17 32-9 27 41-4 15 23z"/><path d="M281 235q56-70 93-39l-17 32 9 27-41-4-15 23z"/></g>}
        <g className="support-mascot-breathe">
          {Array.from({length:12},(_,i)=><g key={i} transform={`translate(200 215) rotate(${i*30})`}><ellipse cx="0" cy="-102" rx="23" ry="52" fill={`url(#${petal})`} stroke={accent} strokeWidth="1.5"/></g>)}
          <path d="M102 175Q98 110 175 103Q247 77 295 132Q339 192 303 274Q276 324 203 331Q124 318 99 265Q80 218 102 175Z" fill={`url(#${body})`} stroke="#d1bcff" strokeWidth="2"/>
          <g opacity=".7" fill="#f5efff">{[ [120,170], [185,139], [253,155], [286,188], [206,191], [115,285], [256,302], [208,314], [137,202], [276,273] ].map(([x,y],i)=><circle key={i} cx={x} cy={y} r={i%3 ? 2 : 3}/>)}</g>
          <ellipse cx="151" cy="332" rx="22" ry="13" fill={accent}/><ellipse cx="245" cy="332" rx="22" ry="13" fill={accent}/>
          <g className="support-mascot-eyes" fill={`url(#${eye})`}>
            <ellipse cx="149" cy="225" rx="28" ry="36"/><ellipse cx="248" cy="225" rx="28" ry="36"/>
            <path d="m142 211 6-11 6 11 11 6-11 5-6 11-6-11-11-5zm99 0 6-11 6 11 11 6-11 5-6 11-6-11-11-5z" fill="#ffdf89"/>
            <circle cx="139" cy="207" r="4" fill="white"/><circle cx="238" cy="207" r="4" fill="white"/>
          </g>
          <ellipse cx="116" cy="252" rx="18" ry="11" fill="#f3a1d2" opacity=".6"/><ellipse cx="282" cy="252" rx="18" ry="11" fill="#f3a1d2" opacity=".6"/>
          <path className="support-mascot-mouth" d="M183 257Q200 280 219 257Q202 290 183 257Z" fill="#2f204e"/>
          <path d="m192 285 8-6 8 6-8 9z" fill={accent}/>
          {form === 'hardware' && <g stroke="#f7d3a0" strokeWidth="5"><rect x="111" y="199" width="76" height="49" rx="15" fill="#111e39" fillOpacity=".4"/><rect x="210" y="199" width="76" height="49" rx="15" fill="#111e39" fillOpacity=".4"/><path d="M187 212h23M112 208l-16-7M286 208l17-7"/></g>}
        </g>
        <g className="support-mascot-halo"><ellipse cx="201" cy="64" rx="40" ry="11" stroke="#f1d38c" strokeWidth="4" transform="rotate(-22 201 64)"/>
          <path d="m201 26 5 11 12 2-9 8 2 12-10-6-11 6 3-12-9-8 12-2z" fill="#f9df92"/></g>
      </g>
      {form === 'snack' && <g className="support-snack"><path d="M129 325h142l-14 33H143z" fill="#58416f" stroke={accent} strokeWidth="3"/>
        <ellipse cx="200" cy="325" rx="71" ry="10" fill="#241c3c" stroke={accent} strokeWidth="3"/><path d="m200 297 7 12 14 2-10 10 2 14-13-7-13 7 2-14-10-10 14-2z" fill="#ffdf8f"/></g>}
      {form === 'hardware' && <g className="support-rune" stroke={accent} strokeWidth="3"><rect x="285" y="294" width="46" height="40" rx="4" fill="#19263d"/><path d="M297 290v-7m12 7v-7m12 7v-7M297 336v7m12-7v7m12-7v7M297 305h22v18h-22z"/><path d="m73 328 26-27 8 9-26 27z" fill="#789dad"/></g>}
      <g className="support-reaction-spark" fill={accent}><path d="m62 98 4 11 11 4-11 4-4 11-4-11-11-4 11-4zm272 3 3 9 9 3-9 3-3 9-3-9-9-3 9-3z"/></g>
    </svg>
  );
}
