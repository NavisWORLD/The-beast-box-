'use client';
import { useCallback, useEffect, useState } from 'react';
import { useBeastSession } from './beast-session';
import { exportSession, shownName } from '../lib/companion/session.mjs';
import { minimalSnapshot } from '../lib/muse/snapshot.mjs';
import { LINK_EVENT, museApi, museCodeSnippet, readLink, writeLink } from '../lib/muse/client';
import MetaMuseQr from './meta-muse-qr';
import styles from './meta-muse.module.css';

type Method = { id: string; label: string; available: boolean; how: string };
type Storage = { configured: boolean; kind: string; missing: string[]; connectorUrl: string; serverCardUrl?: string; pairingMethods?: Method[] };
type Grant = { id: string; kind: 'oauth' | 'pat'; client: string; scope: string; readOnly: boolean; createdAt: string; lastUsedAt: string | null };
type Status = { paired: boolean; deviceId?: string | null; deviceName?: string | null; serverCardUrl?: string; createdAt: string; lastActivityAt: string | null; lastActivity: { tool: string; at: string; via: string } | null; connections: Grant[]; pendingActions: number; snapshotSyncedAt: string | null };

const when = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'never');

async function copy(text: string, done: (msg: string) => void) {
  try { await navigator.clipboard.writeText(text); done('Copied.'); } catch { done('Copy failed. Select the text and copy it by hand.'); }
}

/** Pair with Meta Muse: connector URL, pairing code, Muse Code token and snippet, status, unpair. */
export default function MetaMusePanel() {
  const { ready, session, trail } = useBeastSession();
  const [storage, setStorage] = useState<Storage | null>(null);
  const [linked, setLinked] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [consent, setConsent] = useState(false);
  const [code, setCode] = useState<{ code: string; expiresAt: string; link?: string } | null>(null);
  const [deviceName, setDeviceName] = useState('');
  const [nameTouched, setNameTouched] = useState(false);
  const [access, setAccess] = useState<'read' | 'care'>('read');
  const [token, setToken] = useState<{ token: string; scope: string; expiresAt: string } | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const beast = session?.beast;
  const defaultName = `Beast Box · ${beast ? shownName(beast) : 'my beast'}`.slice(0, 60);
  const shownDeviceName = nameTouched ? deviceName : (status?.deviceName || defaultName);
  const connectorUrl = storage?.connectorUrl || (typeof window !== 'undefined' ? window.location.origin + '/api/mcp' : '/api/mcp');

  const refresh = useCallback(async () => {
    const link = readLink();
    setLinked(!!link);
    if (!link) { setStatus(null); return; }
    const res = await museApi('link', { secret: link.deviceSecret });
    if (res.status === 401) { writeLink(null); setLinked(false); setStatus(null); setMessage('This browser was unpaired.'); return; }
    if (res.ok) setStatus(res.data);
  }, []);

  useEffect(() => {
    void museApi('storage').then((res) => { if (res.data) setStorage(res.data); });
    void refresh();
    const on = () => { void refresh(); };
    window.addEventListener(LINK_EVENT, on);
    return () => window.removeEventListener(LINK_EVENT, on);
  }, [refresh]);

  async function pair() {
    if (!consent || busy) return;
    setBusy(true); setMessage('');
    const snapshot = session ? minimalSnapshot(exportSession(session), trail) : undefined;
    const res = await museApi('link', { method: 'POST', body: { consent: 'share-beast-snapshot', snapshot, deviceName: shownDeviceName } });
    setBusy(false);
    if (!res.ok) { setMessage(res.data?.error_description || res.data?.error || 'Pairing is unavailable right now.'); return; }
    writeLink({ deviceSecret: res.data.deviceSecret, linkedAt: new Date().toISOString(), applied: [] });
    setStatus(res.data);
    setMessage('Paired. Now make a pairing code for the Muse app, or a token for Muse Code.');
  }
  async function makeCode() {
    const link = readLink(); if (!link) return;
    const res = await museApi('code', { method: 'POST', secret: link.deviceSecret, body: {} });
    if (res.ok) setCode(res.data); else setMessage(res.data?.error_description || 'Could not make a pairing code.');
  }
  async function saveName() {
    const link = readLink(); if (!link) return;
    const res = await museApi('device', { method: 'POST', secret: link.deviceSecret, body: { name: shownDeviceName } });
    if (res.ok) { setNameTouched(false); setMessage(`Device name saved: ${res.data.deviceName}. It appears in the Beast Box server card.`); void refresh(); }
    else setMessage(res.data?.error_description || 'Could not save the device name.');
  }
  async function makeToken() {
    const link = readLink(); if (!link) return;
    const res = await museApi('pat', { method: 'POST', secret: link.deviceSecret, body: { access } });
    if (res.ok) { setToken(res.data); void refresh(); } else setMessage(res.data?.error_description || 'Could not make a token.');
  }
  async function revoke(id: string) {
    const link = readLink(); if (!link) return;
    await museApi('grant?id=' + id, { method: 'DELETE', secret: link.deviceSecret });
    void refresh();
  }
  async function unpair() {
    const link = readLink(); if (!link) return;
    setBusy(true);
    await museApi('link', { method: 'DELETE', secret: link.deviceSecret });
    setBusy(false);
    writeLink(null); setLinked(false); setStatus(null); setCode(null); setToken(null);
    setMessage('Unpaired. Every Meta Muse token for this beast is revoked and the server copy is deleted.');
  }

  const snippet = museCodeSnippet(connectorUrl, token?.token);
  return <div className={styles.panel} data-meta-muse-panel="true">
    <h2>Pair with Meta Muse</h2>
    <p className={styles.muted}>Let Meta Muse, Meta&apos;s personal AI agent, read your beast and, if you allow it, feed, play with, rename and talk to it. Beast Box connects as an MCP connector. This is not the Muse EEG headband.</p>

    <div className={styles.box}>
      <span className={styles.label}>Connector URL</span>
      <code className={styles.code}>{connectorUrl}</code>
      <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void copy(connectorUrl, setMessage)}>Copy URL</button></div>
    </div>

    <div className={styles.box}>
      <label className={styles.label} htmlFor="mm-device-name">Device name</label>
      <div className={styles.row} style={{ marginTop: 6 }}>
        <input id="mm-device-name" className={styles.input} style={{ fontSize: 14, letterSpacing: 0, textTransform: 'none', flex: 1, minWidth: 0 }} maxLength={60} value={shownDeviceName} onChange={(e) => { setNameTouched(true); setDeviceName(e.target.value); }} />
        {linked ? <button type="button" className={styles.secondary} onClick={() => void saveName()}>Save name</button> : null}
      </div>
      <p className={styles.small}>Shown to MCP clients in the Beast Box server card and as the server title after connecting.</p>
    </div>

    <div className={styles.status} role="status">
      <i className={`${styles.dot} ${linked ? styles.on : ''}`} aria-hidden="true" />
      <span>{linked ? `Paired${beast ? ` · ${shownName(beast)}` : ''} · last activity ${when(status?.lastActivityAt)}${status?.lastActivity ? ` (${status.lastActivity.tool})` : ''} · last sync ${when(status?.snapshotSyncedAt)}` : 'Not paired. Nothing leaves this browser.'}</span>
    </div>

    {storage && !storage.configured ? <p className={styles.error} role="alert">Connector storage is not configured on this deployment, so pairing is off. Needed: {storage.missing.join(', ')}.</p> : null}

    {!linked ? <div className={styles.box}>
      <label className={styles.check}><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>Share a minimal snapshot of {beast ? shownName(beast) : 'my beast'} with the Beast Box connector while paired: name, species, element, stage, mood, stats, care values, seed provenance, moves and Lost Cosmos progress. Not chat history, memory or sensors. No model training.</span></label>
      <div className={styles.row}><button type="button" className={styles.primary} disabled={!consent || busy || !ready || (storage ? !storage.configured : false)} onClick={() => void pair()}>Pair this beast</button></div>
    </div> : <>
      <div className={styles.box}>
        <span className={styles.label}>Muse app pairing code</span>
        {code ? <><p className={styles.big} aria-label="Pairing code">{code.code}</p><p className={styles.small}>One use. Expires {when(code.expiresAt)}. Type it on the Beast Box consent page when Muse asks to connect, then pick Read only or Read + care actions.</p>
          {code.link ? <div className={styles.row} style={{ alignItems: 'flex-start' }}>
            <MetaMuseQr value={code.link} label="QR code with the connector URL and pairing code" />
            <div style={{ flex: 1, minWidth: 160 }}>
              <p className={styles.small}>Scan on the phone where Muse runs, or open the one-tap link. It carries the connector URL, device and this code (in the #fragment, never sent to a server).</p>
              <div className={styles.row}><a className={styles.secondary} href={code.link} target="_blank" rel="noreferrer" data-meta-muse-onetap="true">Open one-tap link</a><button type="button" className={styles.secondary} onClick={() => void copy(code.link!, setMessage)}>Copy link</button></div>
            </div>
          </div> : null}</> : <p className={styles.small}>Make a code when Muse opens the Beast Box consent page. A QR code and one-tap link come with it.</p>}
        <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void makeCode()}>{code ? 'New pairing code' : 'Show pairing code'}</button></div>
      </div>
      <div className={styles.box}>
        <span className={styles.label}>Muse Code token</span>
        <div className={styles.row}>
          <label className={styles.radio}><input type="radio" name="mm-access" checked={access === 'read'} onChange={() => setAccess('read')} /> Read only</label>
          <label className={styles.radio}><input type="radio" name="mm-access" checked={access === 'care'} onChange={() => setAccess('care')} /> Read + care actions</label>
          <button type="button" className={styles.secondary} onClick={() => void makeToken()}>Make token</button>
        </div>
        {token ? <p className={styles.small}>Shown once ({token.scope.includes('beast.care') ? 'read + care' : 'read only'}, expires {when(token.expiresAt)}). Beast Box keeps only a hash.</p> : null}
      </div>
    </>}

    <div className={styles.box}>
      <span className={styles.label}>Muse Code mcp_servers snippet</span>
      <code className={styles.code} data-muse-snippet="true">{snippet}</code>
      <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void copy(snippet, setMessage)}>Copy snippet</button></div>
    </div>

    {linked && status?.connections?.length ? <div className={styles.box}>
      <span className={styles.label}>Connections</span>
      <ul className={styles.list}>{status.connections.map((g) => <li key={g.id}>
        <span>{g.client} · {g.readOnly ? 'Read only' : 'Read + care'} · used {when(g.lastUsedAt)}</span>
        <button type="button" className={styles.danger} onClick={() => void revoke(g.id)}>Revoke</button>
      </li>)}</ul>
    </div> : null}

    {linked ? <div className={styles.row}><button type="button" className={styles.danger} disabled={busy} onClick={() => void unpair()}>Unpair</button>{status ? <span className={styles.small}>{status.pendingActions} care action{status.pendingActions === 1 ? '' : 's'} waiting to sync</span> : null}</div> : null}

    <div className={styles.box}>
      <span className={styles.label}>How clients find Beast Box</span>
      <p className={styles.small}>Standard discovery from the site URL: /.well-known/ai-catalog.json → server card ({status?.serverCardUrl || storage?.serverCardUrl || '/api/mcp/server-card'}), /.well-known/oauth-protected-resource and /.well-known/oauth-authorization-server, with dynamic client registration.</p>
      <ul className={styles.list}>{(storage?.pairingMethods || []).map((m) => <li key={m.id} data-pairing-method={m.id}><span>{m.available ? '✓' : '✗'} {m.label}{m.available ? '' : ` · ${m.how}`}</span></li>)}</ul>
    </div>

    {message ? <p className={styles.small} role="status">{message}</p> : null}
    <p className={styles.note}>The Muse app lists connectors under Settings &gt; Connectors only after Meta reviews and approves them. Until then, use the Muse Code snippet above. The owner can submit Beast Box through the Muse Connector Platform (Meta review and business verification). Beast Box has not submitted it.</p>
    <p className={styles.small}>Talk replies come from the Beast Box game companion model, an in-character game character, not a conscious mind.</p>
  </div>;
}
