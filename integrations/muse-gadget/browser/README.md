# Browser side: wiring the Pair button to the gadget bridge

[`beastbox-bridge-client.mjs`](beastbox-bridge-client.mjs) is a standalone ES
module (no dependencies) for the "Pair with Meta Muse" panel. It is **not yet
wired into `apps/beastbox-cloud`**; that app was out of scope for this change.
Copy the file into the app (for example `apps/beastbox-cloud/lib/muse-gadget-bridge.mjs`)
when you wire it, and keep the honest labels.

## The flow in the panel

1. User enters the gadget's bridge URL once (e.g. `http://beastbox-pi.local:8787`; the
   installer prints it). Keep it in localStorage.
2. **Pair** → `bridge.startPairing({ label })` → show `code` big, with a
   10-minute countdown and the hint: *"On your Beast Box gadget run
   `musegadget-beastbox link CODE`, or tell Muse 'link my Beast Box browser
   with code CODE'."*
3. `await bridge.waitForLink()` → show "Linked".
4. `bridge.connect(handler)` keeps the stream open and reconnects; show
   `onStatus` (`connecting`, `connected`, `offline`, `revoked`).
5. **Unpair** → `bridge.revoke()`.

The browser can't do the Bluetooth part; the Muse app pairs with the gadget
itself (see the main README). Say so in the panel.

## Example (React, inside `BeastSessionProvider`)

```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { BeastBoxBridge, createSessionHandler, summarizeBeast } from '../lib/muse-gadget-bridge.mjs';
import { care, train, talkAndGrow } from '../lib/companion/adventure.mjs';
import { shownName } from '../lib/companion/session.mjs';
import { buildMoveset, pickAttack } from '../lib/companion/beast-moves.mjs';
import { useBeastSession } from './beast-session';

export function MuseGadgetPair({ url }: { url: string }) {
  const { session, change } = useBeastSession();
  const latest = useRef(session);
  latest.current = session;
  const bridge = useRef<BeastBoxBridge | null>(null);
  const [code, setCode] = useState('');
  const [status, setStatus] = useState('unlinked');

  function connect(b: BeastBoxBridge) {
    void b.connect(createSessionHandler({
      change, getSession: () => latest.current,
      care, train, talkAndGrow, shownName, buildMoveset, pickAttack,
      // Play the attack in the cage/arena; listen for this event there.
      onAttack: (move) => window.dispatchEvent(new CustomEvent('beastbox:muse-attack', { detail: move })),
      onStatus: setStatus,
    }));
  }

  useEffect(() => {
    const b = new BeastBoxBridge({ url });
    bridge.current = b;
    if (b.linked) connect(b);
    return () => b.disconnect();
  }, [url]);

  async function pair() {
    const b = bridge.current!;
    const { code } = await b.startPairing({ label: navigator.userAgent.slice(0, 40) });
    setCode(code);
    await b.waitForLink();
    setCode('');
    connect(b);
  }

  // Keep the gadget's view fresh when the beast changes in the page.
  useEffect(() => { if (status === 'connected') void bridge.current?.pushState(summarizeBeast(session, shownName)); }, [session, status]);

  return (
    <section>
      <p>Muse pairs with your Beast Box gadget over Bluetooth. This links the gadget to the beast in this browser.</p>
      {code ? <p>Code: <strong>{code}</strong> — run <code>musegadget-beastbox link {code}</code> on the gadget.</p> : null}
      <button type="button" onClick={() => void pair()} disabled={!!code}>Pair</button>
      <button type="button" onClick={() => void bridge.current?.revoke().then(() => setStatus('unlinked'))}>Unpair</button>
      <p>Bridge: {status}. A game companion, not a conscious being.</p>
    </section>
  );
}
```

`createSessionHandler` maps `feed` → `care(draft, 'feed')`, `play` →
`care(draft, 'spark' | 'pet')` or `train(draft, hits, 6)`, `talk` →
`talkAndGrow(draft, text)`, `attack` → `pickAttack(buildMoveset(genome))` +
`onAttack(move)`, `moves`, `status`, and `lost_cosmos` (pass `lostCosmos()` if the
page can report progress). Each mutation goes through the provider's
`change()`, so the beast saves like any other care action, and the new summary
goes back to Muse.

Tested in `tests/bridge_client.test.mjs` against the real bridge with the real
`lib/companion` functions in Node.
