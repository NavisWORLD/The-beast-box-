# CST 004: predeclared held-out shadow ablation

This is a **numerical/mechanistic stress test**, not a trained model accuracy benchmark. The frozen protocol is in protocol.json, checked into Endsupdate on main before execution.

The question: does the unmodified eta=1 information component survive binary64 summation at synthetic stellar scales? The control changes ONLY eta to zero, retaining identical positions, masses, velocities, and geometry. Separate shuffled-information, zero-information, and classical-energy controls check sensitivity and implementation. The micro-scale sensitivity arm uses the previously disclosed Parameters from experiment 002; it is **not** a physics observation or evidence of model quality.

256 independent seeded synthetic cases are generated for each arm (3 entity scores per case). No coefficients are fitted on this holdout; the default candidate normalization remains fixed. All output data are preserved as Actions artifacts. The source guard checks original vs copied dyn12 Git blob equality and exact frozen model/scorer source hashes. It rejects direct cst_candidate imports into those frozen files. This is *not* a proof that no other code can ever import CST.

No operational mapping from SI energies and hypothetical information bits to a 12-scalar software-state drive has been established, and the frozen A-B-A model score inputs contain no corrected CST signal. To avoid manufactured causality, the experiment runs the CST computation in **read-only shadow mode**; it does not modify runtime, memory, model weights, or policy. If a nonzero numeric component is below score precision, report that null. If a score changes on synthetic inputs, report only that local observability. A model-performance claim requires a scientifically justified bridge, appropriate independent outcomes, and a separately registered actual matched model experiment.

One repository-root workflow file (endsupdate-cst-ablation-004.yml) is used to run isolated source inside Endsupdate; no existing root code/evidence is modified. GitHub Actions compares Python 3.10 and 3.12. Raw evidence: Endsupdate/evidence/endsupdate-cst-ablation-004.json (generated, not checked in).

**Status before execution:** neither PASS nor model improvement is predeclared. The result must be read from this run's evidence.
