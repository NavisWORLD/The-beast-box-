# Beast Awakens: retained genesis inputs and collision census

This audit starts from main revision `aab168e607e5b9a896ead547bfeb88ffc499ccff` and the actual public Spark generator. It makes no provider request, runs no new quantum job, changes no saved Beast, and preserves the complete paged gallery. Retained IBM count integrity, archived source provenance, deterministic art diversity, and model performance are separate questions.

## Reproduce and consume

```sh
node scripts/audit-creature-genesis.mjs --sources-only
node scripts/audit-creature-genesis.mjs --write
node scripts/audit-creature-genesis.mjs --check
node --test apps/beastbox-cloud/tests/audit-creature-genesis.test.mjs apps/beastbox-cloud/tests/spark-source-registry.test.mjs
```

The script needs Node 20 or newer and no third-party package. `--write` replaces only generated files under `experiments/beast-awakens-001/genesis`; `--check` recomputes their exact bytes. The full stream is `creature-records.jsonl.gz`, with gzip mtime zero and OS byte 255. Its manifest includes the decompressed SHA, byte length and 5,676 record count; `gzip -dc experiments/beast-awakens-001/genesis/creature-records.jsonl.gz` reads every record. The compressor version is recorded for exact compressed-byte reproduction. Historical Stage015 objects must be present locally for that part of the evidence to reproduce; the script disables Git lazy fetching and reports missing objects explicitly. It never queries the original provider. Source-code byte digests capture local changes as well as the baseline revision.

`loadGenesisSources({root})` exports `{root, archiveRuns, sortedArchiveRuns, qvmRuns, rowSources, sources}`. `archiveRuns` preserves gallery order. `sortedArchiveRuns` sorts the same real records by run key for experiments. `rowSources` maps each run key to its original relative JSON path, file digest and zero-based row index. `qvmRuns` is separate. Browser `loadSparkRuns()` remains the 5,676-row IBM gallery; `loadSparkRuns({includeQvm:true})` explicitly permits replay of the 24 pinned simulator batches. Neither loading operation saves or adopts a creature.

## Published measurement archives

Every row passes independent Node SHA-256 comparison against its retained canonical count hash, exact binary width, nonnegative safe-integer counts, positive shot total, and unique run key. The browser registry now applies the same count integrity checks and rejects conflicting records sharing a key. These checks establish consistency of retained data, not independent hardware attestation.

| Public file, relative to `apps/beastbox-cloud/public/spark/` | Distributions | Jobs | Shots | Raw file SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `runs.json` | 5,580 | 171 | 25,214,976 | `d984c1393c82d6b12199009e268981dd86815d088a2201a765a89a63b8bae078` |
| `user-seeds-20261004-1.json` | 24 | 24 | 98,304 | `b6f644ca3007fe050dd89b8be888ff90cf5c342c98807cb957241086a5dfcaab` |
| `user-seeds-20261004-2.json` | 24 | 24 | 98,304 | `16639bc458fdbca66c55e8ac5d43a7350b5e1707524f7bdaa30a09327fc642e5` |
| `user-seeds-20261004-3.json` | 24 | 24 | 74,328 | `c31791920605d974409873a79577bf185ca0218b03449749c298c342f65f4571` |
| `user-seeds-20261004-4.json` | 24 | 24 | 90,468 | `7eabb77ed4b38465a123e95b1f1718fb8cb3e0007bfd100fabf14b5ce6261e83` |
| Combined, unique keys | **5,676** | **267** | **25,576,380** | Individual source digests retained in JSON evidence |

The seed index digest is `4701cac9b7388169112cc75190a60f830dba91d1703129d00cf03a60681435ee`. The Python base table `spark-beasts/data/quantum_runs.compact.json` is byte-identical to public `runs.json`. Backends contribute Fez 2,192, Kingston 2,737, Marrakesh 688 and Torino 59 distributions. Bit widths are 1-bit 5,184, 2-bit 7, 4-bit 1, 5-bit 196 and 12-bit 288. The 96 added seed rows came from 109 usable uploaded jobs after 13 existing jobs were excluded; the index records one missing result.

The upload index explicitly omits raw circuits, user/account identifiers and original signal payloads. The compact pack has no per-job creation timestamps. Backend names and job IDs are retained classifications, not a fresh provider response.

## Actual generator and observed morphology

`public/spark/genome.mjs` builds `lost-cosmos-beast-genome-v2`. Its seed is SHA-256 of sorted canonical JSON containing full counts, backend, job ID, PUB index, shots, bucketed focus/calm/spark traits, schema and optional public keeper label. Run key and the declared count hash do not directly enter the seed. `buildGenome` buckets traits to tens with Python-compatible rounding before hashing.

Counts feed three two-bit probability packets, a 12-number drive and a deterministic nine-step classical transform. This is a software representation; a one-bit run repeats bit indices and cannot contain twelve independent measured dimensions. Fourteen numerical art genes combine that transform with seeded classical streams. Body, island, appendages, names, habits and voice choices also use hash-derived streams. Hash avalanche can reroll art when only job metadata changes.

The census uses every real row, the existing gallery's three trait recipes in ordinal-modulo-three order, null keeper, bucket 10, open eyes and stages I–III. It generates all 5,676 creatures without failures or artificial saved fixtures.

| Category | Actual counts in this cohort |
| --- | --- |
| Seven profile families | aurora 840; memory 830; nebula 814; plasma 776; signal 891; starlight 750; void 775 |
| Eleven bodies | axolotl 453; biped 610; bird 248; dragonling 636; fish 546; fox 692; golem 429; moth 286; pup 776; serpent 551; sprout 449 |
| Seven gaits | bob 772; float 500; hop 742; pulse 760; scuttle 858; sway 905; wobble 1,139 |
| Six procedural voice styles | beep 401; chirp 1,657; coo 1,090; growl 769; purr 838; trill 921 |
| Poses | front 2,815; side 1,780; three-quarter 1,081 |
| Islands / elements | Cinder Drift/ember 1,290; Eridoria Prime/verdant 804; Hollow Verdance/grove 760; Rust Meridian/machine 458; Crown/radiant 410; Pale Expanse/frost 507; Shattered Reef/crystal 1,093; Umbral Deep/umbral 354 |

The JSON summary additionally inventories twelve ear shapes, twelve tail shapes, eight wing choices, nine patterns, eyes, mouth, glow, facing, twelve habits, eight quirks, four oscillator waveforms and all fourteen gene ranges. Eight temperament labels are supported in code; this particular three-recipe cohort observes five. Families are separate classical profile categories, chosen by FNV-1a of `spark-family|seed`; they are not measured biological or quantum classifications. The profile's ten statistics and all stage statistics are fictional game values.

`voice.mjs` derives deterministic utterance text and synthesis envelopes from voice parameters, utterance index, stage and drive. It schedules WebAudio oscillators and filters; it does not run a learned voice model. The audit hashes the complete voice parameters and fixed neutral utterance envelopes for each stage. It does not claim distinct recorded audio from envelope hashes: a waveform experiment must separately record sample rate, channel count, frame count, synthesis implementation and raw PCM digest.

## Equivalences and collisions

| Compared material | Distinct digests | Repeated groups | Different-material digest conflicts |
| --- | ---: | ---: | ---: |
| Canonical raw counts | 3,091 | 1,376, covering 3,961 records | 0 |
| Rounded engine dyn12 under the assigned recipe | 2,802 | 688, covering 3,562 records | 0 |
| Full seed preimage / 256-bit seed | 5,676 | 0 | 0 |
| 32-bit public profile ID compared against full seeds | 5,676 | 0 | 0 |
| Full canonical genome; phenotype; QBEAST genesis; QBEAST snapshot | 5,676 each | 0 | 0 |
| Stage I, II and III raw RGBA pixels | 5,676 each | 0 | 0 |
| Behavior; voice parameters; fixed stage utterance envelopes | 5,676 each | 0 | 0 |

Repeated counts are identical input distributions, not SHA-256 collisions. Rounded dyn12 equivalence also occurs when different provenance or information discarded by the transform produces the same retained vector. The short `bb-xxxxxxxx` ID is only 32-bit FNV-1a, so absence of aliases in this cohort does not make it a collision-free identity or authentication key. Experiments and archives must retain full seeds, source keys and complete digests; they must not deduplicate by name, family, rendered look or short ID.

The retained control pair `ibm_kingston:da680fk86m6s738vgm00#pub1` and `ibm_kingston:da69g1c6l22c73dm1mf0#pub29` has count digest `49c83391f4655d01c87dceaabc9dde8d3e1377b31f3904130285b6fc97094ad1`. At fixed 40/40/40 traits, it has identical raw counts and dyn12, but different seeds, phenotypes and stage-II pixels. Setting the second record's backend/job/PUB/shots/run key to the first produces identical seeds, phenotypes and pixels. Therefore visual diversity alone cannot establish additional quantum information or a hardware-specific benefit.

Each census record preserves exact recipe and original source-row references, expanded-run hash, full seed, short ID, categories, and every digest. SHA-256 hashes raw source bytes, canonical UTF-8 JSON, or exact 16,384-byte 64×64 RGBA arrays as stated. QBEAST hashes use their literal `QBEAST1\0` domain. Phenotype hashing excludes only `schema`, `seed`, `inputs`, `quantum` and `engine`; it retains all visual, behavior, voice, names and game-stat fields. Every repeated digest is checked against the complete preimage bytes, not a second copy of its digest. The cohort digest hashes the ordered array of full record digests. `digest-manifest.json` records artifact bytes and hashes, excludes its own self-hash, and enforces a 16 MiB maximum per file. Generation errors remain explicit and make the audit command fail.

## IBM receipts and scientific source limits

Two full committed SamplerV2 results in `experiments/zeref-origin-heart-001/source/ibm/` are decoded from their compressed NumPy BitArrays. Both are 5-bit, 4,096-shot results, match manifest raw and canonical hashes, and exactly reproduce their public archive counts:

- Marrakesh `d93d8pgoamcc73dc3afg`, completed, created `2026-07-02T21:13:10.961006Z`; raw result SHA `9c1691d318c23f10c0d9d67cb50bb791536c415675146e20ad1e85eca596b1a3`.
- Kingston `d93jnlq47v0s73823aj0`, completed, created `2026-07-03T04:34:31.945452Z`; raw result SHA `a44dcd7b3bc82395d319b5e9439dc8dca01c84d6c516a13ddb724288941d0fab`.

Committed info files are sanitized account projections. Their hashes legitimately differ from `raw_info_sha256` for unsanitized originals; the evidence records both roles. No raw circuit is published for these two jobs. A third historical Marrakesh record, `da1mqfcdedkc73er87r0`, has 4,096 verified counts and digest `dfddf5366961cab837ae614750efb1dd60121ac3b3f6b7506d39346e3fd7bdce`, matching its archive row. Its contemporaneous "fresh" flag does not mean this audit executed fresh hardware. Its record expressly denies new quantum entropy in synthetic continuation and waveform generation.

Ten additional Fez hardware-witness records retain external repository/revision/path digests. This audit preserves those references without claiming to reauthenticate their remote originals. The sealed whole-organism resource-source status says `SCIENTIFICALLY_CLOSED_NO_CAUSAL_CONSUMER_EDGE`; the IBM path says `NOT_RUN_NO_SEALED_PREREGISTERED_CAUSAL_PATH`. Historical hardware provenance is not evidence that a model requires that resource or receives quantum-specific intelligence.

## Rigetti QVM and Stage015

`public/spark/rigetti-qvm-sim.json` has raw SHA `ced9a9c99427f87821b0d9da986fba5597dbf64dbe7a5e49283b81dfffd1acba`. Its actual canonical `scenario_records` hash is `7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599`, identical to the full Stage015 Azure receipt at pinned Git revision `cd5d9321cb30f5327d14bbdd3f71751b630d81a3`. There are eight conditions, 24 distinct `rigetti.sim.qvm` jobs and 2,048 simulated shots: history A 512, history B 512, held-out future 1,024. The declared source is `NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU`, with zero physical jobs permitted.

All 24 program commitments reproduce the documented Quil text `DECLARE ro BIT[2]`, `RESET`, `RX(theta to 12 decimals) 0`, `CNOT 0 1`, and the two measurements, each line terminated by newline. The public projection retains program hashes rather than raw submitted program text, and omits per-job provider creation timestamps. Reconstructing a committed program is not evidence of a new submission. This simulator benchmark has only 00/11 outcomes. These are classical simulator observations, not Rigetti hardware receipts. Only historical Git evidence is examined; Azure account identity and job execution are not independently reauthenticated here.

Pinned Stage015 receipt paths are `evidence/stage015/azure-qvm-24-job-public-receipt.json`, `qwen-192-forecast-public-receipt.json` and `independent-audit.json`. Their byte hashes, retained scores and limitations are in `source-inventory.json`. The offline independent audit reports 24 source receipts, 24 program checks, 2,048 shots and 192 rescored model generations.

Stage015 ran frozen `Qwen/Qwen2.5-1.5B-Instruct`, revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, over eight QVM scenarios and 24 separately generated local classical scenarios, with six arms per scenario. CNS12 was prompt context; no model weights or neural state were updated. Cloud ideal-probability MAE was 0.15821145 for CNS12 versus 0.02116310 for the classical summary/Jeffreys estimate. Local CNS12 MAE was 0.18742552 versus 0.06810082 for the model's classical-summary arm and 0.02602974 for non-model Jeffreys. Those retained results do not show a CNS12 forecasting improvement. Source labels were disclosed and the task's stationary Bernoulli success count is sufficient; label compliance is not blinded source identification. The separate documented native 14K studies are different experiments and must not be merged into the 192-generation Stage015 receipt.

## Portable format boundaries

| Format | Actual retained content | Boundary |
| --- | --- | --- |
| Full package QBEAST1/v1 | Bounded public profile, optional approved 12-number projection, host progress, hash-linked public events, snapshot digest, optional Ed25519 signature | 512 KiB and 512 events; strict JSON/schema checks. Privileged progress/projection needs a host-pinned signing key. Embedded key alone is untrusted. Signature covers UTF-8 hex digest. Verification grants no authority. |
| Public Spark QBEAST1 subset | Classical profile, zero/unavailable public projection, zero host progress, public recipe memory and lineage | Up to 2,048 events in Spark identity validation. Counts/full genome are not embedded; replay requires the approved run registry. This event bound differs from the full package and is not universal compatibility. |
| BCG1 | 60 bytes: magic/version/look/measured flag, uint32 checkpoint sequence, 24 signed little-endian Q8.8 values for 12 CNS + 12 synaptic coordinates | Default is unmeasured zeros. Approved checkpoint receipt required for measured export; rejects invalid range. No binary signature/CRC, executable model, private memory or quantum processor. |
| BCP1 | 64 bytes: family/look, ten fictional statistics, five temperament weights, cosmetic hue, 32-bit public ID, reserved zeros, CRC32 | CRC32 checks transport errors, not provenance. No full seed, CNS state, learned model, owner memory or credentials. Four 64×64 4bpp sprites and 16-color palette are separate game assets. |

See `packages/quantum-beast/src/verifier.ts`, `apps/beastbox-cloud/public/spark/{qbeast,identity}.mjs`, `apps/beastbox-cloud/lib/gba-companion.ts`, `docs/COSMIC_GENESIS_GBA_BCP1.md` and the GBA module's `AGENTS.md`. Native game stage and ordinary browser-local care are not host-approved biological evolution or intelligence evidence.

## Inputs and controls for the next experiment

Freeze source-file and code digests before selecting outcomes. Use the validated full archive, or an explicitly declared receipt-backed subset, with a fixed sorted order and preregistered source selection. Treat QVM and local classical samples as separate classes. Retain failures and duplicates; do not select only appealing morphology or successful model responses.

Run paired controls with identical traits, keeper, bucket, shot budget, bit width and rendering/synthesis settings: exact replay; same-count different-job metadata; metadata-normalized source-blind inputs; fixed/uniform/zero-drive inputs; and seeded local classical samples with matched probability/correlation structure. Record the local control algorithm and RNG seed. Permuting record order, bit labels or counts is an explicit intervention with its own provenance. Do not relabel classical controls as IBM or physical Rigetti evidence.

Preregister quantitative endpoints appropriate to the question: repeatability, source traceability, full-genome and pixel uniqueness, defined morphology distributions, calibrated held-out prediction, or a defined model-state intervention. Compare art diversity against classical seed diversity before claiming source-specific value. For forecasting, exclude future counts and hidden theta from every prompt/state/selection step, commit prompt digests at the inference boundary, and compare with a calibrated classical estimator. Separate train/test by source job and count-equivalence group to avoid replay leakage. Report multiplicity, invalid answers, paired uncertainty and null results. Current inventory establishes reproducible deterministic generation and retained provenance; it establishes no consciousness, quantum advantage, new physical dimension or hardware-specific intelligence.
