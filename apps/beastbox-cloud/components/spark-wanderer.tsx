'use client';
import { useEffect, useState } from 'react';
import type { CreatureProfile } from '../lib/creature-profile';
import { wanderFrame } from '../lib/companion/wander.mjs';
import SparkBeastCompanion from './spark-beast-companion';
import css from './spark-wanderer.module.css';

type Props = {
  profile?: CreatureProfile | null;
  pulse?: string;
  thinking?: boolean;
};

export default function SparkWanderer({ profile, pulse = '', thinking = false }: Props) {
  const [tick, setTick] = useState(0);
  const [reaction, setReaction] = useState(0);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(media.matches);
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    if (!pulse) return;
    setReaction(36);
  }, [pulse]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setTick((value) => value + 1);
      setReaction((value) => (value > 0 ? value - 1 : 0));
    }, 180);
    return () => window.clearInterval(id);
  }, []);

  const frame = wanderFrame(tick, reaction, thinking, reduced);
  return <div className={css.lane} data-spark-wander="true" data-wander-mode={frame.mode}>
    <div className={css.beast} style={{ transform: `translate3d(${frame.x}px, ${frame.y}px, 0)` }}>
      <SparkBeastCompanion profile={profile} fallbackLook={profile?.baseLook ?? 'nebula'} compact state={frame.visual === 'thinking' ? 'thinking' : frame.visual === 'celebrating' ? 'celebrating' : frame.visual === 'observing' ? 'observing' : 'idle'} label="Spark Beast wandering the chat" />
    </div>
  </div>;
}
