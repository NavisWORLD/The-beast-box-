import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft, ArrowUpRight, CheckCircle2, FlaskConical, Orbit, ShieldCheck } from 'lucide-react';
import styles from './stage015.module.css';

export const metadata: Metadata = {
  title: 'COSMOS Lab // Stage 015 — Beast Box',
  description: 'Original Azure Rigetti cloud QVM simulator evidence, 192 pinned Qwen inference trials and independently audited COSMOS 12D forecasting controls.',
  robots: { index: true, follow: true },
};

const repo = 'https://github.com/NavisWORLD/The-beast-box-';
const source = repo + '/blob/experiment/cosmos-qvm-meaningful-015/evidence/stage015';
const conditions = [
  { name: 'No history', azure: 0.29211446, local: 0.30328752 },
  { name: 'Raw history', azure: 0.07497938, local: 0.11606159 },
  { name: 'Classical statistics', azure: 0.02116310, local: 0.06810082 },
  { name: 'Actual COSMOS CNS7 12D', azure: 0.15821145, local: 0.18742552 },
  { name: 'Shuffled CNS7 12D', azure: 0.19209025, local: 0.15863485 },
  { name: 'Input-drive classical control', azure: 0.18031048, local: 0.20548397 },
] as const;

export default function Stage015Research() {
  return <main className={styles.root}>
    <div className={styles.glow} aria-hidden="true" />
    <header className={styles.header}>
      <Link href="/" className={styles.brand}><Orbit size={22} aria-hidden="true"/> BEAST BOX <span>// COSMOS LAB</span></Link>
      <Link href="/" className={styles.back}><ArrowLeft size={15} aria-hidden="true"/> Back to Beast Box</Link>
    </header>

    <section className={styles.hero} aria-labelledby="report-title">
      <div className={styles.eyebrow}><span className={styles.statusDot} aria-hidden="true" /> PUBLISHED RESEARCH // 26 SEP 2026</div>
      <h1 id="report-title">THE QUANTUM<br/><em>FEEDBACK ENGINE</em><br/><span>STAGE 015</span></h1>
      <p className={styles.lead}>Real experiments. Public receipts. Both the positive engineering milestone and the negative scientific result.</p>
      <p className={styles.byline}>CORY DAVIS / NAVISWORLD · COSMOS / RAWRPHØS / COSMIC SYNAPSE THEORY</p>
      <div className={styles.actions}>
        <a className={styles.primary} href={repo + '/pull/125'} target="_blank" rel="noopener noreferrer">Open the research PR <ArrowUpRight size={17} aria-hidden="true"/></a>
        <a className={styles.secondary} href={repo + '/blob/experiment/cosmos-qvm-meaningful-015/docs/COSMOS_STAGE015_VERIFIED_RESULTS_AND_LIMITATIONS.md'} target="_blank" rel="noopener noreferrer">Technical report <ArrowUpRight size={15} aria-hidden="true"/></a>
      </div>
    </section>

    <section className={styles.metrics} aria-label="Verified experiment counts">
      <article><strong>24</strong><span>AZURE CLOUD QVM JOBS</span><small>Rigetti simulator, not QPU</small></article>
      <article><strong>2,048</strong><span>SIMULATED MEASUREMENTS</span><small>Held-out future batches</small></article>
      <article><strong>192</strong><span>ACTUAL MODEL GENERATIONS</span><small>Frozen public Qwen 1.5B</small></article>
      <article><strong>6</strong><span>EXPERIMENTAL CONDITIONS</span><small>Including classical controls</small></article>
    </section>

    <section className={styles.section} aria-labelledby="architecture-title">
      <div className={styles.sectionHead}><FlaskConical size={19} aria-hidden="true"/> <span>01 / A WORKING EXPERIMENTAL PIPELINE</span></div>
      <h2 id="architecture-title">We connected the parts. <em>Then we measured.</em></h2>
      <p>Historical observations from independently executed Azure-hosted Rigetti QVM simulator jobs passed through the existing COSMOS SOUL and signal-fusion path into BridgePacket, CNS7 and the evolving dyn12 state. A pinned public open-weight model then forecast independent future simulator observations.</p>
      <div className={styles.flow} role="list" aria-label="Recorded experimental processing path">
        {['Rigetti cloud QVM', 'SOUL + signal fusion', 'BridgePacket', 'CNS7 → dyn12', 'Qwen forecast', 'Blinded scoring'].map((item,i)=><div role="listitem" className={styles.step} key={item}><small>0{i+1}</small>{item}</div>)}
      </div>
      <p className={styles.note}>The 12D state was supplied as model-facing prompt context. This experiment did not change Qwen's neural weights, produce physical quantum measurements, or establish a new physics result.</p>
    </section>

    <section className={styles.section} aria-labelledby="results-title">
      <div className={styles.sectionHead}><CheckCircle2 size={19} aria-hidden="true"/> <span>02 / RECORDED RESULTS</span></div>
      <h2 id="results-title">Here&apos;s what <em>actually happened.</em></h2>
      <p>Mean absolute error against the concealed ideal probabilities for two separately evaluated cohorts. Lower means less prediction error. Eight scenarios used genuine Azure cloud simulator outputs; 24 separate scenarios used reproducible local classical simulation.</p>
      <div className={styles.tableScroll} tabIndex={0} aria-label="Horizontally scrollable Stage 015 prediction-error table">
        <table className={styles.table}>
          <thead><tr><th scope="col">MODEL INPUT CONDITION</th><th scope="col">AZURE QVM (8)</th><th scope="col">LOCAL CLASSICAL (24)</th></tr></thead>
          <tbody>{conditions.map(row=><tr key={row.name}><th scope="row">{row.name}</th><td>{row.azure.toFixed(5)}<span className={styles.bar}><i style={{width: Math.round(row.azure/0.33*100)+'%'}}/></span></td><td>{row.local.toFixed(5)}<span className={styles.bar}><i style={{width: Math.round(row.local/0.33*100)+'%'}}/></span></td></tr>)}</tbody>
        </table>
      </div>
      <div className={styles.reference}><span>NON-LLM CLASSICAL JEFFREYS POSTERIOR REFERENCE</span><strong>Azure: 0.02116 <b>·</b> Local: 0.02603</strong></div>
    </section>

    <section className={styles.finding} aria-labelledby="finding-title">
      <div className={styles.sectionHead}><ShieldCheck size={19} aria-hidden="true"/> <span>03 / THE HONEST SCIENTIFIC FINDING</span></div>
      <h2 id="finding-title">The pipeline worked.<br/><em>12D did not improve this forecast.</em></h2>
      <p>Providing interpretable classical statistics reduced prediction error in this task. The actual COSMOS/CNS7 12D prompt-context condition did not demonstrate additional predictive value over those same statistics. That is a meaningful measured limitation, not evidence of quantum advantage or AGI.</p>
      <p>The model was explicitly told its data came from a simulator, so source-label responses were instruction compliance, <strong>not blind simulator-provenance detection</strong>. Also, the classical matched control transformed the input drive; matching the final state norm was not independently established.</p>
      <p>Next hypothesis: test time-varying, independently measured external signals against equally informative classical filtering and rigorously matched state controls. This would be a separate preregistered experiment, not a reinterpretation of Stage 015.</p>
    </section>

    <section className={styles.section} aria-labelledby="evidence-title">
      <div className={styles.sectionHead}>04 / TRACEABLE EVIDENCE</div>
      <h2 id="evidence-title">Don&apos;t take our word. <em>Check the receipts.</em></h2>
      <div className={styles.evidence}>
        <a href={source+'/azure-qvm-24-job-public-receipt.json'} target="_blank" rel="noopener noreferrer"><span>01</span><strong>Sanitized cloud simulator job receipt</strong><small>24 job identifiers, hashes, counts and source digest</small><ArrowUpRight size={19} aria-hidden="true"/></a>
        <a href={source+'/qwen-192-forecast-public-receipt.json'} target="_blank" rel="noopener noreferrer"><span>02</span><strong>Frozen Qwen generation transcript</strong><small>All 192 generated answers, error metrics and controls</small><ArrowUpRight size={19} aria-hidden="true"/></a>
        <a href={source+'/independent-audit.json'} target="_blank" rel="noopener noreferrer"><span>03</span><strong>Independent offline evidence audit</strong><small>Source hashes, local cohort and regraded model answers</small><ArrowUpRight size={19} aria-hidden="true"/></a>
        <a href={repo+'/actions/runs/36244583047'} target="_blank" rel="noopener noreferrer"><span>04</span><strong>Independent GitHub Actions verification</strong><small>Successful offline audit; no fresh provider jobs</small><ArrowUpRight size={19} aria-hidden="true"/></a>
      </div>
      <p className={styles.note}>The GitHub receipts record cloud simulator executions, not physical QPU results. Artifact auditing does not independently authenticate Azure billing or account ownership.</p>
    </section>
    <footer className={styles.footer}><Link href="/">✺ BEAST BOX</Link><span>CORY DAVIS · COSMOS · MODEL ≠ MEMORY · RESEARCH ≠ HYPE</span><a href={repo+'/pull/125'} target="_blank" rel="noopener noreferrer">OPEN RESEARCH PR ↗</a></footer>
  </main>;
}
