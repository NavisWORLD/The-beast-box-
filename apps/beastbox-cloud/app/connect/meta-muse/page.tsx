import type { Metadata } from 'next';
import { headers } from 'next/headers';
import { checkAuthorizeRequest, SCOPE_CARE } from '@/lib/muse/auth.mjs';
import { mcpUrl, museStore } from '@/lib/muse/server';
import styles from '@/components/meta-muse.module.css';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'Pair Beast Box with Meta Muse', robots: { index: false, follow: false } };

type Search = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || '';
const FIELDS = ['client_id', 'redirect_uri', 'response_type', 'code_challenge', 'code_challenge_method', 'state', 'scope', 'resource'];

/** OAuth 2.1 authorization endpoint: the beast owner enters the pairing code shown in Beast Box and picks the access level. */
export default async function MetaMuseConsent({ searchParams }: { searchParams: Promise<Search> }) {
  const q = await searchParams;
  const h = await headers();
  const host = h.get('x-forwarded-host') || h.get('host') || 'localhost';
  const proto = h.get('x-forwarded-proto') || (host.startsWith('localhost') || host.startsWith('127.') ? 'http' : 'https');
  const origin = `${proto}://${host}`;
  const store = museStore();
  const p = Object.fromEntries(FIELDS.map((k) => [k, one(q[k])]));
  let problem = '';
  let clientName = 'An MCP client';
  if (!store) problem = 'This Beast Box deployment has no connector storage configured yet, so it cannot pair.';
  else {
    try { const client = await checkAuthorizeRequest(store, p, mcpUrl(origin)); clientName = client.client_name; }
    catch (e) { problem = e instanceof Error ? e.message : 'Invalid authorization request.'; }
  }
  const askedCare = !p.scope || p.scope.split(/\s+/).includes(SCOPE_CARE);
  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="mm-title">
        <p className={styles.eyebrow}>Beast Box connector</p>
        <h1 id="mm-title">Pair your beast with {problem ? 'Meta Muse' : clientName}</h1>
        {problem ? <p className={styles.error} role="alert">{problem}</p> : (
          <form method="post" action="/api/muse/oauth/authorize">
            {FIELDS.map((k) => p[k] ? <input key={k} type="hidden" name={k} value={p[k]} /> : null)}
            <p className={styles.muted}>Open Beast Box on the device where your beast lives, choose <b>Pair with Meta Muse</b>, and type the one-time code it shows. The code works once and expires after 10 minutes.</p>
            {one(q.pair_error) ? <p className={styles.error} role="alert">That pairing code is wrong, expired or already used. Make a new one in Beast Box.</p> : null}
            <div className={styles.field}>
              <label htmlFor="pairing_code">Pairing code</label>
              <input id="pairing_code" className={styles.input} name="pairing_code" placeholder="ABCD-2345" autoComplete="one-time-code" inputMode="text" maxLength={9} required />
            </div>
            <fieldset className={styles.choices} style={{ border: 0, padding: 0, margin: '12px 0' }}>
              <legend className={styles.label}>What may it do?</legend>
              <label className={styles.choice}>
                <input type="radio" name="access" value="read" defaultChecked />
                <div><strong>Read only</strong><span>See the beast&apos;s name, species, element, stage, mood, stats, seed provenance, care values, Lost Cosmos progress and moves. It cannot change anything.</span></div>
              </label>
              <label className={styles.choice} aria-disabled={!askedCare}>
                <input type="radio" name="access" value="care" disabled={!askedCare} />
                <div><strong>Read + care actions</strong><span>Also feed, play with, rename and talk to the beast. These change only this beast&apos;s care save. Nothing is bought, sent or shared.{askedCare ? '' : ' (This client asked for read only.)'}</span></div>
              </label>
            </fieldset>
            <p className={styles.small}>Shared with the connector: a minimal beast snapshot your browser syncs while paired. Not shared: chat history, memory, sensors, owner Brain Bay data. No model training. You can unpair any time in Beast Box.</p>
            <div className={styles.row}>
              <button className={styles.primary} type="submit" name="decision" value="allow">Allow</button>
              <button className={styles.secondary} type="submit" name="decision" value="deny" formNoValidate>Deny</button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
}
