'use client';

import { useState } from 'react';
import { Github, Heart, Sparkles, X } from 'lucide-react';

export default function CosmicSupportWidget() {
  const [open, setOpen] = useState(false);

  return (
    <aside className={`cosmic-support ${open ? 'is-open' : ''}`} aria-label="Support Beast Box">
      {!open ? (
        <button
          type="button"
          className="cosmic-support-launcher"
          onClick={() => setOpen(true)}
          aria-expanded="false"
          aria-label="Open support panel"
        >
          <span className="support-orb" aria-hidden="true">✦</span>
          <span className="support-launcher-copy">
            <small>OPEN SOURCE · INDEPENDENT</small>
            <strong>Feed the Beast</strong>
          </span>
          <Heart size={18} aria-hidden="true" />
        </button>
      ) : (
        <div className="cosmic-support-panel">
          <div className="support-constellation" aria-hidden="true">
            <i/><i/><i/><i/><i/>
          </div>
          <button
            type="button"
            className="support-close"
            onClick={() => setOpen(false)}
            aria-label="Close support panel"
          >
            <X size={17}/>
          </button>

          <p className="support-kicker"><Sparkles size={14}/> FUEL THE LIVING COSMOS</p>
          <h2>Keep the strange little universe alive.</h2>
          <p className="support-copy">
            Beast Box is open source. Support helps cover hosting, compute, hardware prototypes,
            documentation, experiments, and the time it takes to keep shipping.
          </p>

          <div className="support-fuel" aria-label="Ways support helps">
            <span>✦ tiny sparks matter</span>
            <span>☄ monthly fuel</span>
            <span>◌ one-time boosts</span>
          </div>

          <a
            className="support-primary"
            href="https://github.com/sponsors/NavisWORLD"
            target="_blank"
            rel="noreferrer"
          >
            Sponsor on GitHub <Github size={18}/>
          </a>
          <a
            className="support-secondary"
            href="https://buymeacoffee.com/cosmic_syanpse"
            target="_blank"
            rel="noreferrer"
          >
            Send a one-time cosmic coffee <Heart size={16}/>
          </a>

          <p className="support-honesty">
            No fake counters. No artificial scarcity. The open-source core stays open.
          </p>
        </div>
      )}
    </aside>
  );
}
