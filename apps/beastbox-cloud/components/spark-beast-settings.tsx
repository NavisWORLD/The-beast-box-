'use client';
import Link from 'next/link';
import {Sparkles} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import {useCompanion} from './companion-provider';
import {generateCreature} from '../lib/creature-profile';

/**
 * Browser-only visual/game settings for the active companion.
 * This surface never changes provider choice, owner authority, COSMOS memory,
 * or device permissions.
 */
export default function SparkBeastSettings(){
 const {profile,selectProfile,clearProfile}=useCompanion();
 return <article className="data-card wide" aria-label="Spark Beast companion settings">
  <div className="cloud-connect-heading"><Sparkles size={20}/><div><h2>SPARK BEAST · COMPANION</h2><p>One browser-local game identity across Customize, the owner dock, Game Lab and the Lost COSMOS handoff.</p></div></div>
  <SparkBeastCompanion profile={profile} fallbackLook={profile?.baseLook??'nebula'} controls label="Spark Beast settings preview"/>
  <div className="insight-line"><span>Active game profile</span><b>{profile?profile.name+' · '+profile.family:'DEFAULT PREVIEW'}</b></div>
  <div className="insight-line"><span>Sprite source</span><b>Recorded-seed Spark renderer</b></div>
  <div className="insight-line"><span>Voice</span><b>Local WebAudio · tap to play</b></div>
  <div className="insight-line"><span>SIM EARTH embedded here</span><b>NO</b></div>
  <div className="insight-line"><span>Model / memory / authority changed by these controls</span><b>NO</b></div>
  <p>Stage buttons are appearance previews only. Lost COSMOS keeps earned XP, bond and evolution in its shared care/game ledger. Recorded quantum counts seed the fictional creature renderer; there is no live quantum connection.</p>
  <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
   <Link className="outline-action" href="/beast-cage#customize">Open full Customize ↗</Link>
   {!profile?<button className="outline-action" type="button" onClick={()=>selectProfile(generateCreature('beastbox-owner-starter','signal'))}>Create a starter Beast</button>:
    <button className="outline-action" type="button" onClick={clearProfile}>Clear browser game profile</button>}
  </div>
 </article>;
}
