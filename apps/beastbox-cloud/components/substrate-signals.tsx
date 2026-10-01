'use client';
type EventRecord = Record<string, unknown>;
export default function SubstrateSignals({events}:{events:EventRecord[]}) {
  const measured = events.filter(e => {
    const signals=e.signals;
    return signals !== null && typeof signals==='object' && !Array.isArray(signals)
      && (signals as Record<string,unknown>).schema==='substrate-signal-v1';
  }).slice(-3);
  return <section aria-label="Measured substrate signals">
    <span>MEASURED COSMOS SIGNALS ({measured.length} visible)</span>
    <p>Only checkpoint-backed signal receipts. Empty results are not replaced with simulated values.</p>
    {measured.length===0?<p role="status">No compatible measured signal receipt available from this runtime.</p>:
      measured.map((record,i)=><div className="record" key={String(record.sequence??i)}>
        <small>REAL CHECKPOINT SEQUENCE {String(record.sequence??'unreported')}</small>
        <pre style={{overflowWrap:'anywhere',whiteSpace:'pre-wrap'}}>{JSON.stringify(record.signals,null,2)}</pre>
      </div>)}
  </section>;
}
