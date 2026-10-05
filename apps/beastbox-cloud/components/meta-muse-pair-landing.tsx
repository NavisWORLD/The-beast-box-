'use client';
import { useEffect, useState } from 'react';
import { parsePairingFragment } from '../lib/muse/pairing-link.mjs';
import { museCodeSnippet } from '../lib/muse/client';
import styles from './meta-muse.module.css';

export default function MetaMusePairLanding() {
  const [info, setInfo] = useState<{ connector: string; code: string; device: string } | null>(null);
  const [name, setName] = useState('');
  const [note, setNote] = useState('');
  useEffect(() => {
    const parsed = parsePairingFragment(window.location.hash);
    // Only this site's own connector is ever shown, so a crafted link cannot point you elsewhere.
    const own = window.location.origin + '/api/mcp';
    if (parsed.connector && parsed.connector !== own) parsed.connector = '';
    setInfo(parsed);
    if (parsed.device && parsed.connector) {
      void fetch(parsed.connector + '/server-card?device=' + encodeURIComponent(parsed.device), { headers: { Accept: 'application/mcp-server-card+json' } })
        .then((r) => (r.ok ? r.json() : null)).then((card) => { if (card?.title) setName(card.title); }).catch(() => undefined);
    }
  }, []);
  const copy = async (text: string) => { try { await navigator.clipboard.writeText(text); setNote('Copied.'); } catch { setNote('Copy failed. Select the text and copy it by hand.'); } };
  if (!info) return <p className={styles.muted}>Reading the pairing link…</p>;
  if (!info.connector) return <><p className={styles.eyebrow}>Beast Box connector</p><h1>Pairing link not valid here</h1><p className={styles.error}>This link is incomplete or names a different connector. Open Pair with Meta Muse in Beast Box and scan its QR code again.</p></>;
  return <div className={styles.panel} data-meta-muse-landing="true">
    <p className={styles.eyebrow}>Beast Box connector</p>
    <h1>Connect {name || 'Beast Box'} to Meta Muse</h1>
    <ol className={styles.muted} style={{ paddingLeft: 18 }}>
      <li>If your Muse lets you add a custom connector by URL, use this one. Otherwise paste the Muse Code snippet below into Muse Code.</li>
      <li>When Muse opens the Beast Box consent page, type the pairing code and choose Read only or Read + care actions.</li>
    </ol>
    <div className={styles.box}><span className={styles.label}>Connector URL</span><code className={styles.code}>{info.connector}</code>
      <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void copy(info.connector)}>Copy URL</button></div></div>
    {info.code ? <div className={styles.box}><span className={styles.label}>Pairing code</span><p className={styles.big}>{info.code}</p>
      <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void copy(info.code)}>Copy code</button></div>
      <p className={styles.small}>One use, 10 minutes. It travels in this link&apos;s #fragment, which is not sent to any server.</p></div> : null}
    <div className={styles.box}><span className={styles.label}>Muse Code mcp_servers snippet</span><code className={styles.code}>{museCodeSnippet(info.connector)}</code>
      <div className={styles.row}><button type="button" className={styles.secondary} onClick={() => void copy(museCodeSnippet(info.connector))}>Copy snippet</button></div></div>
    {note ? <p className={styles.small} role="status">{note}</p> : null}
    <p className={styles.note}>Muse does not discover third-party devices on its own: Meta has no public device-pairing API for them. The Muse app lists connectors under Settings &gt; Connectors only after Meta approves them. Until then, Muse Code is the dependable way to connect.</p>
  </div>;
}
