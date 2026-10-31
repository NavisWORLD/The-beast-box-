# zeref-heart-seed-v11

- **RECORDED IBM hardware CHSH** (a new real measurement, source_class RECORDED_IBM_HARDWARE): job `dbj7a40nceqs73ajd2d0` on `ibm_marrakesh` (qubits 97,107, cz), 24,000 rounds, 1 shot each. Quantum wins **20,194** (84.14% +/- 0.24%) vs classical control **17,973** (74.89%); classical bound 75%. Not loophole-free (one chip, one controller, no readout mitigation, os.urandom questions).
- Owner-authorized 2026-10-31; Cory waived the 60 s reserve for this run. Cap 81 s (server-enforced). Open Plan remaining 86 s before, 76 s after.
- outcomes_sha256 `d5a56fd01b51cdbaffd583c615e5cf75d87a33d7b738b4568fb3b0d746ff3fda`; full result file sha256 `ec2d0c94eacc04d8ba68b48997d896799694b187dd2763a47432151d1d5295ef`. Run https://github.com/NavisWORLD/The-beast-box-/actions/runs/41251258966
- **Heart seed v11** `bfc35208bb21af82c308f2fb0d882de74e5cf559756567f83bcbf9ddfa5d0322` = sha256(json.dumps(mix, sort_keys=True)) over v10 hash + this job + its outcomes and result-file hashes. No bio packet in this mix (no new heartbeat was measured).
- Not published: question lists, commitment salts, per-round outcomes, private question files, raw media.
