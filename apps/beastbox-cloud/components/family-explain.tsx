'use client';

import { useEffect, useState } from 'react';
import { explainCreature } from '../lib/companion/family-explain.mjs';
import styles from './family-explain.module.css';

const MODE_KEY = 'beastbox-cage-mode-v1';

type Mode = 'friendly' | 'advanced';

const LABELS: Record<string, string> = {
  provider: 'Provider',
  hardwareClass: 'Hardware class',
  jobId: 'Job',
  timestamp: 'Time',
  shots: 'Shots',
  counts: 'Counts',
  circuitHash: 'Circuit hash',
  receiptDigest: 'Receipt digest',
  creatureId: 'Creature',
  growthEventId: 'Growth event',
  validation: 'Validation',
  quota: 'Quota',
  error: 'Error',
  checkpoint: 'Checkpoint',
};

const CODE_FIELDS = new Set(['provider', 'jobId', 'circuitHash', 'receiptDigest', 'creatureId', 'growthEventId']);

function isMode(value: unknown): value is Mode {
  return value === 'friendly' || value === 'advanced';
}

function shown(value: unknown) {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

export default function FamilyExplain({ input, mode }: { input?: object | null; mode?: Mode }) {
  const [stored, setStored] = useState<Mode>('friendly');
  useEffect(() => {
    if (isMode(mode)) return;
    try {
      const saved = window.localStorage.getItem(MODE_KEY);
      if (isMode(saved)) setStored(saved);
    } catch {
      /* storage unavailable */
    }
  }, [mode]);
  const resolved: Mode = isMode(mode) ? mode : stored;
  const view = explainCreature(input ?? {}, { mode: resolved });
  const advanced = view.advanced as Record<string, unknown> | null;
  const rows = advanced
    ? Object.entries(advanced).filter(([, value]) => value !== null && value !== undefined && value !== '')
    : [];
  const id = input && typeof input === 'object' && 'id' in input ? (input as { id?: unknown }).id : null;
  const creatureKey = typeof id === 'string' && id ? id : 'none';
  return (
    <section className={styles.family} aria-label="Creature explanation" data-family-explain={creatureKey} data-mode={resolved}>
      <h2>Seed</h2>
      <p>{view.friendly.seed}</p>
      <h2>Remembers</h2>
      <p>{view.friendly.memory}</p>
      <h2>Doing</h2>
      <p>{view.friendly.behavior}</p>
      <h2>Growth</h2>
      <p>{view.friendly.growth}</p>
      <h2>Next</h2>
      <p>{view.friendly.next}</p>
      {advanced ? (
        <details className={styles.advanced}>
          <summary>Advanced record</summary>
          {rows.length ? (
            <dl className={styles.list}>
              {rows.map(([key, value]) => (
                <div key={key} className={styles.row}>
                  <dt>{LABELS[key] ?? key}</dt>
                  <dd>{CODE_FIELDS.has(key) ? <code>{shown(value)}</code> : shown(value)}</dd>
                </div>
              ))}
            </dl>
          ) : <p>No advanced fields on this record.</p>}
        </details>
      ) : null}
    </section>
  );
}
