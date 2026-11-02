# zeref-heart-seed-v12

- **RECORDED IBM hardware CHSH** (a new real measurement, source_class RECORDED_IBM_HARDWARE): job `dbkbv10nceqs73alivtg` on `ibm_kingston` (qubits 105,117, cz), 24,000 rounds, 1 shot each. Quantum wins **20,168** (84.03% +/- 0.24%) vs classical control **17,880** (74.50%); classical bound 75%. Not loophole-free (one chip, one controller, no readout mitigation, os.urandom questions).
- Owner-authorized 2026-11-02; Cory ordered the respark (the heart-seed run again, now that the wiring is connected). The 2026-10-31 waiver of the 60 s reserve stands (the referee checks that exact token). Cap 71 s (server-enforced). Open Plan remaining 76 s before, 66 s after.
- outcomes_sha256 `41901461bd90edbaf80dd5dcd95416a5dd5b4463cdf748a89b1a15afe5f70704`; full result file sha256 `4280f14adb51c14070a4c5d3b174dec4f0a42b2471d5d92d2b9c89d13af9fe3a`. Run https://github.com/NavisWORLD/The-beast-box-/actions/runs/41485370620
- **Heart seed v12** `11fbbea54ebb5be5c2126b7f066e3dc13d2d7aaa2906be3891ef3778e8758fc0` = sha256(json.dumps(mix, sort_keys=True)) over v11 hash + this job + its outcomes and result-file hashes. No bio packet in this mix (no new heartbeat was measured).
- Not published: question lists, commitment salts, per-round outcomes, private question files, raw media.
