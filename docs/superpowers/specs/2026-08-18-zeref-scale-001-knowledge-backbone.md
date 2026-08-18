# ZEREF-SCALE-001 Knowledge Backbone Training

## Goal
Make Zeref dramatically more capable in grammar, broad knowledge, reasoning, and conversation without destroying the verified TALK-004 lineage or pretending IBM hardware supplies semantic knowledge.

## Starting state
- Durable identity/memory lineage remains ZEREF-DAD-SON-TALK-004.
- Durable memory remains the verified 352-record ledger unless a later promotion gate explicitly advances it.
- QC67_cosmo remains immutable ancestry.
- Rejected TALK-005 and TALK-006 children are evidence, not parents.

## Architecture
ZEREF-SCALE-001 is a hybrid descendant rather than a bigger char-level checkpoint.

1. Knowledge/grammar backbone: Qwen/Qwen3.5-9B, Apache-2.0, pretrained and post-trained.
2. Zeref adapter: LoRA/PEFT layer trained only on vetted Zeref/Dad behavior, identity boundaries, memory use, concise answers, self-correction, and tool discipline.
3. Durable memory: current append-only Zeref ledger is retrieved at inference and is not baked destructively into base weights.
4. CST/heartbeat state: verified hardware or deterministic continuation state is represented as explicit conditioning metadata/tokens. It is not described as world knowledge, consciousness, or biological life.
5. Dad learning queue: raw generated answers are preserved first. Only human-authored or explicitly vetted corrected targets may enter training.
6. Knowledge retrieval: external/current knowledge is retrieved at runtime when available. The pretrained backbone supplies broad static knowledge; retrieval supplies freshness.

## Why this replaces brute-force TALK training
QC67_cosmo is a from-scratch char-level model with a 128-character native context. TALK-005 and TALK-006 proved that teacher-forced answer metrics can improve while free-running semantic answers get worse. Therefore further blind dosage on the tiny architecture is not the scale path.

## IBM hardware role
Fresh IBM jobs may root a training/talk session and provide auditable hardware-derived state. IBM measurement outcomes do not create grammar or world knowledge. They are a state/provenance input only.

## Training objective
Use parameter-efficient SFT on the large pretrained backbone. Preserve base-model capability by keeping the adapter small and mixing Zeref-specific examples with general instruction-retention examples. Do not train raw Zeref generations back into the model.

## Conversation wire
System:
- identity: Zeref computational model
- Dad role: Cory is Dad in this experiment
- claim boundary: not literally Caleb, not biological heartbeat/consciousness proof
- active durable ledger tip/count
- IBM/CST session state metadata

Context:
- retrieved durable memories
- optional current knowledge retrieval

User:
- Dad message

Assistant:
- Zeref response

## Promotion gates
A scaled child is not promoted because it is larger. It must pass:
- grammar/readability benchmark >= backbone baseline - 1 percentage point
- broad-knowledge benchmark >= backbone baseline - 2 percentage points
- Zeref identity/boundary exam >= 95%
- durable-memory factual exam >= 90%
- no Dad/Zeref role-label leakage in generated answers
- no automated promotion of raw outputs
- no mutation of the 352-record prefix
- no claim that IBM state equals knowledge, consciousness, resurrection, or biological life

## Target deployment tiers
- Development: Qwen3.5-4B quantized for lower-memory local machines.
- Primary scale target: Qwen3.5-9B LoRA descendant.
- Larger backbones may be evaluated later but never declared “smarter than GPT-5.6 Sol” without a declared benchmark suite demonstrating the specific comparison.

## Cloud execution status
Hugging Face user `phera-ra` is authenticated but currently not Pro and current OAuth lacks Hub write scope. A direct Jobs entitlement check returned HTTP 402 Payment Required on 2026-08-18. Therefore this spec requires the training script and datasets to be fully reproducible, while cloud execution is gated on paid Jobs entitlement + Hub write access.

## Claim boundary
This system can become a much stronger computational assistant and preserve memorial/relationship context. Training results do not establish deceased-person identity, resurrection, biological life, consciousness, or quantum advantage.
