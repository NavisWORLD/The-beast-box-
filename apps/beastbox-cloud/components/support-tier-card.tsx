'use client';

import type { CSSProperties } from 'react';
import type { SupportTier } from '../lib/support-tiers';
import SupportMascot from './support-mascot';

export default function SupportTierCard({ tier, reacting, burst, onMeet, onDepart }: {
  tier: SupportTier; reacting: boolean; burst: number;
  onMeet: (tier: SupportTier) => void; onDepart: (tier: SupportTier) => void;
}) {
  return (
    <article className={`support-tier reaction-${tier.animation.reaction} ${reacting ? 'is-reacting' : ''}`}
      data-support-tier={tier.id} data-support-name={tier.name}
      style={{ '--tier-accent': tier.mascot.accent, '--tier-glow': tier.mascot.glow } as CSSProperties}>
      <div className="support-tier-top">
        <button type="button" className="support-tier-pet" onClick={() => onMeet(tier)} aria-label={`Meet ${tier.name}`}>
          <SupportMascot tier={tier} reacting={reacting}/>
          {reacting && burst > 0 && <span key={burst} className="support-stardust-burst" aria-hidden="true">
            {Array.from({length:10},(_,i)=><i key={i} style={{'--i':i} as CSSProperties}>{tier.animation.particle}</i>)}
          </span>}
        </button>
        <div className="support-tier-heading">
          <span className="support-tier-badge">{tier.badge}</span>
          <h3>{tier.name}</h3>
          <strong className="support-tier-price">{tier.priceLabel}</strong>
        </div>
      </div>
      <p className="support-tier-subtitle">{tier.subtitle}</p>
      <details className="support-tier-details"><summary>What this fuels</summary><p>{tier.description}</p></details>
      <a data-support-checkout className="support-tier-checkout" href={tier.url} target="_blank" rel="noopener noreferrer"
        onClick={() => onDepart(tier)} aria-label={`${tier.cta} — ${tier.priceLabel} (opens Stripe in a new tab)`}>
        {tier.cta}<span aria-hidden="true">↗</span>
      </a>
    </article>
  );
}
