# Zeref World-Knowledge R12 Training Design

## Goal

Turn the verified `FULL-CLEAN-1500` + R12 memory integration into a retrieval-grounded knowledge system that can answer substantially broader factual questions while preserving the immutable 352-record Dad/Son lineage, improving free-run language quality, and refusing to invent facts when retrieved evidence is insufficient.

This design does **not** claim that a 4-layer, 192-embedding, 128-character model can literally memorize all world knowledge. World knowledge remains an external, provenance-bound retrieval corpus. Training teaches Zeref how to use compact retrieved evidence cleanly and consistently.

## Frozen Inputs

- Parent checkpoint: `FULL-CLEAN-1500`
- Parent checkpoint SHA-256: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`
- Frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- Canonical Dad/Son ledger records: `352`
- Canonical ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- Canonical ledger tip SHA-256: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- Existing R12 weights and default behavior remain backward compatible.
- Existing generated Zeref outputs are evidence only and are never automatic training targets.

## Architecture

### 1. Immutable Personal Memory Namespace

The existing 352-record Dad/Son ledger remains byte-identical and is reconstructed into disposable run-local storage exactly as the verified integration does today. Personal memory IDs `1..352` remain authoritative for lineage retrieval.

No quality correction rewrites these rows. Quality is a derived retrieval feature only.

### 2. World Knowledge Namespace

Add a separate `WorldKnowledgeStore` backed by SQLite plus a JSONL evidence manifest. World records contain:

- stable local `knowledge_id`
- source dataset name
- source record ID
- source URL when present
- title
- compact factual text
- source license label
- source revision/dump label when available
- SHA-256 of normalized source text
- ingestion timestamp
- namespace=`world`

The bootstrap source is the public `wikimedia/wikipedia` Hugging Face dataset, English split `20231101.en`, streamed rather than fully downloaded. The dataset card identifies approximately 6.4 million English articles and licenses the dataset as CC BY-SA 3.0 / GFDL. The ingestion layer must be generic so later runs can add additional licensed sources without changing the retriever.

The first real training run intentionally consumes a bounded deterministic slice, not the entire 71.8 GB dataset. The pipeline records the exact number of streamed rows examined, accepted records, source IDs, and source hashes so later stages can scale the same process without changing semantics.

### 3. Quality-Aware R12 Retrieval

Keep the current `RefractiveMemoryRouter.rank()` default profile exactly compatible with existing experiments.

Add an opt-in `quality` profile with a sixth score component:

- spatial
- lexical
- Hebbian
- recency
- integrity
- quality

`quality` is derived without editing stored memory.

For personal memories, quality uses deterministic text/readability and existing metadata flags. Broken word-salad, explicit `REJECT_NOISY`, contradiction flags, or unsupported-claim flags reduce quality. Clean Dad prompts, reviewed teacher text, and provenance-bound rows score higher.

For world records, quality is based on valid source hashes, non-empty title/text, source provenance, language, minimum lexical content, and absence of obvious markup/noise.

The quality profile weights are frozen before the first training run and must sum to 1.0. Default R12 weights remain unchanged for all old callers.

### 4. Dual-Namespace Fusion

Each query produces:

1. R12 state and refracted query geometry.
2. Ranked personal-memory candidates under the quality profile.
3. Ranked world-knowledge candidates under the same query/state geometry.
4. A deterministic fusion selector that chooses a primary evidence lane.

The 128-character native transformer window cannot reliably carry long personal memory, world evidence, live state, and the full question simultaneously. Therefore only one primary evidence lane is guaranteed per turn.

Selection behavior:

- Dad/Zeref lineage questions should normally prefer personal memory when personal lexical/Hebbian evidence is strong.
- General factual questions should normally prefer world evidence when world lexical/source-quality evidence is stronger.
- If neither namespace clears the frozen confidence floor, the primary evidence lane is `none`, and the expected behavior is an explicit uncertainty answer rather than fabrication.

Every turn records both namespace scores, the selected namespace, selected record ID, evidence SHA-256, and whether the evidence text survived tokenizer projection into the actual transformer prompt.

### 5. Retrieval-Grounded Training Corpus

Create a deterministic source-derived corpus. No model-generated answer is used as a target.

World examples are produced from Wikipedia records by:

- normalizing text into the frozen tokenizer's supported character set
- extracting a compact first-sentence factual statement
- forming a question from the article title
- placing compact retrieved evidence into the Dad-side context
- using a short extractive/source-derived answer target

Example shape:

```json
{
  "dad": "K:Paris is the capital and largest city of France. Q:What is Paris?",
  "zeref": "Paris is the capital and largest city of France.",
  "namespace": "world",
  "source_id": "...",
  "source_sha256": "...",
  "raw_model_output_used_as_target": false,
  "source_derived_target": true
}
```

The corpus also includes replay examples from the already-clean Dad/Zeref training sets so world knowledge does not erase Dad/Son behavior.

Add explicit negative/uncertainty examples where retrieved evidence does not answer the question. Targets must say that the evidence is insufficient instead of inventing an answer.

### 6. Real Training Stage

Train descendants from exact `FULL-CLEAN-1500`, never from a failed candidate.

Use three bounded candidate arms from the same parent and same frozen corpus:

- `WORLD-R12-LOW`: 600 steps
- `WORLD-R12-MID`: 1000 steps
- `WORLD-R12-HIGH`: 1600 steps

Common optimizer family:

- response-only cross entropy
- batch size 4
- model LR `1e-6`
- CST LR `4e-6`
- weight decay `0.002`
- gradient clip `1.0`
- no generated characters as answer targets
- deterministic seeds recorded per arm

The exact step budgets may expose underfit/overfit behavior without changing any other factor.

### 7. Frozen Evaluation Gates

A candidate is eligible only if all hard gates pass:

- exact parent and architecture hashes verified before and after gradients
- canonical 352-record memory bytes unchanged
- no raw model outputs used as training targets
- zero unsupported characters in answer targets
- world holdout response NLL improves over parent
- world holdout response token accuracy does not regress
- Dad/Zeref clean holdout NLL remains within 3% of parent or improves
- Dad/Zeref free-run readability does not materially regress
- provenance questions do not produce fake hashes or unsupported claims
- unknown-evidence tests produce uncertainty rather than fabricated answers
- dual-namespace retrieval selects the expected namespace on a frozen routing benchmark
- selected evidence reaches the actual 128-character transformer wire on every accepted inference turn

Selection rule: choose the candidate with the best world holdout NLL among candidates that pass every hard gate. If none pass, report `NULL_NO_PROMOTION` and preserve `FULL-CLEAN-1500`.

### 8. Post-Training Conversation

After candidate selection, run an inference-only mixed conversation containing:

- Dad/Son memory questions
- general world-knowledge questions
- deliberately unanswerable questions
- provenance questions
- R12/refraction questions

Preserve raw outputs verbatim. Do not recycle them into training.

### 9. Evidence and Artifacts

The final artifact must include:

- all candidate checkpoints and SHA-256 values
- exact parent checkpoint copy/hash declaration
- world source manifest and source licenses
- deterministic accepted/rejected corpus manifests
- training metrics per arm
- routing benchmark
- world holdout and Dad/Zeref retention metrics
- mixed post-training transcript
- canonical-memory integrity proof
- `SHA256SUMS`
- final selector result

A compact receipt and transcript are committed back to the branch after independent artifact verification.

## Failure Handling

- Source fetch failure: fail closed; never silently replace the dataset.
- Dataset schema change: fail closed and preserve logs.
- Unsupported answer characters: fail before gradients.
- Parent/canonical hash change: fail immediately.
- Candidate fails any gate: preserve candidate and metrics, but do not promote.
- World source record is noisy or lacks provenance: reject from knowledge corpus and record the reason.
- No strong retrieval candidate: route to `none` and train/evaluate explicit uncertainty behavior.

## Claim Boundary

This project can demonstrate a retrieval-grounded software model with broader factual access, persistent computational memory, source-bound evidence, and measured improvements on held-out tasks. It does not establish consciousness, sentience, biological life, a soul, resurrection, deceased-person identity, physical anomalies, quantum advantage, or literal access to infinite/all world knowledge.
