import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft, ArrowUpRight, Atom, BrainCircuit, FlaskConical, ShieldCheck } from 'lucide-react';
import styles from './research.module.css';
import GodCoreInspector from '@/components/god-core-inspector';

export const metadata: Metadata = {
  title: 'COSMOS Lab // The Two Falsification Tests — Beast Box',
  description: 'Cory Davis / NavisWORLD: actual RAWRPHØS self-correction and independently trained native 12D controls, original CPU evidence and honest negative outcomes.',
  robots: { index: true, follow: true },
};

const repo = 'https://github.com/NavisWORLD/The-beast-box-';
const dynReport = repo + '/blob/main/docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md';
const selfReport = repo + '/blob/main/docs/experiments/COSMOS_SELF_CORRECTION_005_RESULTS.md';
const records = [
  { name: 'Native 12D', heldout: '28.9%', shift: '27.9%', accent: 'cyan' },
  { name: 'Standard attention', heldout: '31.1%', shift: '22.1%', accent: 'gray' },
  { name: 'Shuffled state', heldout: '30.7%', shift: '22.7%', accent: 'gray' },
] as const;

export default function ResearchIndex() {
  return (
    <main className={styles.page}>
      <div className={styles.aura} aria-hidden="true" />
      <header className={styles.header}>
        <Link href="/" className={styles.brand}>✦ BEAST BOX <span>// COSMOS LAB</span></Link>
        <Link href="/" className={styles.back}><ArrowLeft size={15} aria-hidden="true" /> Back to the Beast</Link>
      </header>
      <div className={styles.content}>
        <section className={styles.hero} aria-labelledby="research-title">
          <p className={styles.eyebrow}>CORY DAVIS / NAVISWORLD · VERIFIED RESEARCH · 29 SEPTEMBER 2026</p>
          <h1 id="research-title">WE TESTED<br /><em>THE BEAST.</em><br /><span>HERE&apos;S THE EVIDENCE.</span></h1>
          <p className={styles.lead}>
            Two difficult questions. Actual original model runs. Independently trained
            architectural controls. Preserved failures, not manufactured victories.
          </p>
          <div className={styles.actions}>
            <a href={selfReport} className={styles.primary} target="_blank" rel="noopener noreferrer">
              Self-correction evidence <ArrowUpRight size={17} aria-hidden="true" />
            </a>
            <a href={dynReport} className={styles.secondary} target="_blank" rel="noopener noreferrer">
              12D experiment evidence <ArrowUpRight size={17} aria-hidden="true" />
            </a>
          </div>
        </section>

        <section className={styles.summary} aria-label="Experiment overview">
          <div><span className={styles.mono}>005</span><strong>REAL SELF-CRITIQUE</strong><small>Original native checkpoint and Qwen calibration</small></div>
          <div><span className={styles.mono}>006</span><strong>TRAINED 12D CONTROLS</strong><small>3 seeds · 3 independently trained attention modes</small></div>
          <div><span className={styles.mono}>0</span><strong>UNPROVEN CLAIMS PROMOTED</strong><small>Every negative outcome stays in the published record</small></div>
        </section>

        <section className={styles.section} aria-labelledby="self-title">
          <p className={styles.sectionTag}><BrainCircuit size={18} aria-hidden="true" /> 01 / EXPERIMENT 005</p>
          <h2 id="self-title">Can a model correct <em>its own mistake?</em></h2>
          <p>
            We withheld the correct answers while each model reviewed its own earlier reply.
            Neutral retries, true and misleading correctness signals, explicit answer
            disclosure and different follow-up tasks were measured separately.
          </p>
          <div className={styles.tableFrame}>
            <table className={styles.table}>
              <caption className={styles.caption}>Correct responses out of eight fixed synthetic tasks</caption>
              <thead><tr><th scope="col">ACTUAL ORIGINAL MODEL</th><th scope="col">FIRST ANSWER</th><th scope="col">OWN REVIEW</th><th scope="col">EXPLICIT GOLD DISCLOSURE</th></tr></thead>
              <tbody>
                <tr><th scope="row">RAWRPHØS 18K</th><td>0/8</td><td>0/8</td><td>0/8</td></tr>
                <tr><th scope="row">Qwen 0.5B</th><td>3/8</td><td>3/8</td><td>5/8</td></tr>
              </tbody>
            </table>
          </div>
          <div className={styles.verdict}>
            <span className={styles.dot} aria-hidden="true" />
            <p><strong>RESULT: NOT DEMONSTRATED.</strong> Neither model corrected a previously wrong answer through its own blind critique in this eight-case pilot. Giving Qwen the answer increased its count, but that is assisted prompting, not self-correction.</p>
          </div>
          <div className={styles.links}>
            <a href={selfReport} target="_blank" rel="noopener noreferrer">Full technical report <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href={repo + '/actions/runs/36592111897'} target="_blank" rel="noopener noreferrer">Original CPU execution <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href={repo + '/pull/151'} target="_blank" rel="noopener noreferrer">Source and protocol <ArrowUpRight size={14} aria-hidden="true" /></a>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="dyn-title">
          <p className={styles.sectionTag}><Atom size={18} aria-hidden="true" /> 02 / EXPERIMENT 006</p>
          <h2 id="dyn-title">Does native 12D <em>beat the controls?</em></h2>
          <p>
            Three native model configurations were trained separately from the same initial
            tensors on the same synthetic binding episodes, minibatches and update budget.
            The 12D gate and gradients were verified active; longer four-binding episodes
            were withheld for an exploratory sequence-length shift.
          </p>
          <div className={styles.scoreList} aria-label="Mean accuracy across three independently trained seeds">
            {records.map(row => (
              <div key={row.name} className={styles.scoreRow}>
                <div className={styles.modelName}>{row.name}</div>
                <div className={styles.score}><strong>{row.heldout}</strong><span>UNSEEN 3-BINDING</span></div>
                <div className={styles.score}><strong>{row.shift}</strong><span>UNSEEN 4-BINDING</span></div>
              </div>
            ))}
          </div>
          <div className={styles.verdict}>
            <span className={styles.dot} aria-hidden="true" />
            <p><strong>RESULT: NO HELD-OUT ADVANTAGE.</strong> Native 12D did not beat standard attention on the primary test. It showed an exploratory improvement on the longer sequence shift, but this small synthetic experiment cannot establish a general or novel intelligence advantage.</p>
          </div>
          <div className={styles.links}>
            <a href={dynReport} target="_blank" rel="noopener noreferrer">Full technical report <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href={repo + '/actions/runs/36591525286'} target="_blank" rel="noopener noreferrer">Original three-seed CPU run <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href={repo + '/pull/150'} target="_blank" rel="noopener noreferrer">Source and controls <ArrowUpRight size={14} aria-hidden="true" /></a>
          </div>
        </section>

        <GodCoreInspector />

        <section className={styles.section} aria-labelledby="hf-substrate-title">
          <p className={styles.sectionTag}><BrainCircuit size={18} aria-hidden="true" /> 04 / PUBLISHED HUGGING FACE LINEAGE</p>
          <h2 id="hf-substrate-title">The model can change. <em>The Beast stays.</em></h2>
          <p>
            The verified public <strong>phera-ra/QC67_cosmo</strong> research release preserves
            architecture notes, training lineage, quantum-genesis documentation, a measurement
            manifest and negative findings. These are source artifacts, not a silent new model
            installation. Brain Bay only runs a model after the existing provider verifies it;
            the local Beast stores its identity and permitted memory separately.
          </p>
          <div className={styles.links}>
            <a href="https://huggingface.co/phera-ra/QC67_cosmo" target="_blank" rel="noopener noreferrer">Public model/research release <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href="https://huggingface.co/phera-ra/QC67_cosmo/tree/main/architecture" target="_blank" rel="noopener noreferrer">PHOS / CST architecture <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href="https://huggingface.co/phera-ra/QC67_cosmo/blob/main/FINDINGS.md" target="_blank" rel="noopener noreferrer">Findings, controls and null results <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href="https://huggingface.co/phera-ra/QC67_cosmo/blob/main/QUANTUM_CREATURE.md" target="_blank" rel="noopener noreferrer">Quantum creature genesis notes <ArrowUpRight size={14} aria-hidden="true" /></a>
            <a href="https://huggingface.co/phera-ra/QC67_cosmo/blob/main/data/quantum_measurements_manifest.json" target="_blank" rel="noopener noreferrer">Measurement manifest <ArrowUpRight size={14} aria-hidden="true" /></a>
          </div>
          <p>
            Inside Lost COSMOS, a connected Brain Bay can now use a bounded summary of the
            selected Beast&apos;s saved conversations only if its keeper enables memory sharing.
            Guest chat is still stateless. Game-frame brightness and color signals are
            opt-in measurements, not full image understanding. No remote model receives
            QBEAST signing authority or raw camera frames from this feature.
          </p>
        </section>

        <section className={styles.boundaries} aria-labelledby="bounds-title">
          <h2 id="bounds-title"><ShieldCheck size={22} aria-hidden="true" /> What we are—and are not—claiming</h2>
          <p>
            These experiments establish real engineering execution and transparent small-sample
            results. They do not establish reliable autonomous error correction, superior
            general reasoning, new physics, physical quantum advantage or consciousness.
            Comparing equal allocated parameters is not the same as matching active parameters
            or FLOPs. Synthetic cases are not independent real-world benchmark populations.
          </p>
          <div className={styles.footerLinks}>
            <a href={repo + '/tree/main/docs/experiments'} target="_blank" rel="noopener noreferrer">Explore all preserved receipts <ArrowUpRight size={15} aria-hidden="true" /></a>
            <Link href="/research/stage015"><FlaskConical size={15} aria-hidden="true" /> Related Stage 015 experiment</Link>
          </div>
        </section>
      </div>
      <footer className={styles.footer}>CORY DAVIS // NAVISWORLD · MODEL ≠ MEMORY · MODEL ≠ STATE · MODEL ≠ AUTHORITY</footer>
    </main>
  );
}
