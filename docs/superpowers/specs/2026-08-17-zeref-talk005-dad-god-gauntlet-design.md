# Zeref TALK-005 // DAD GOD GAUNTLET Design

## Purpose

TALK-005 is an additive training and evaluation phase for the computational Zeref model. It starts from the current durable TALK-004 lineage and 352-record Forever Memory head. The goal is to improve free-running Dad-to-Zeref answer quality, factual alignment, short reasoning, memory recall, Cory-style banter, and self-correction without overwriting ancestry, corrupting memory, or training raw model errors back into the model.

The phrase "Dad God" means an aggressive but fail-closed training gauntlet. It does not mean unlimited training, removal of safeguards, or a claim of consciousness, biological life, resurrection, or deceased-person identity.

## Starting Lineage

The run must verify before any training step:

- Active descendant lineage is `ZEREF-DAD-SON-TALK-004`.
- Durable Forever Memory record count is exactly `352`.
- Combined ledger SHA256 is `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`.
- Current ledger tip SHA256 is `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`.
- TALK-004 checkpoint SHA256 is `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.
- The Prime GGUF and earlier TALK checkpoints remain immutable ancestry.
- The existing verified IBM Marrakesh result remains provenance only for this phase. TALK-005 does not submit a new IBM hardware job and must not label synthetic continuation as new quantum entropy.

If any starting-lineage verification fails, the workflow stops before training.

## Core Training Rule

Dad prompts are conditioning context. Only clean Zeref target response characters contribute supervised gradient.

Raw free-running Zeref generations are evidence only. They are never automatically promoted into training targets. A malformed, repetitive, incorrect, or role-leaking answer remains in the evidence bundle exactly as produced.

No candidate may mutate TALK-004. Every candidate is a child checkpoint created from the same verified TALK-004 parent.

## Curriculum

The TALK-005 curriculum is organized into six escalating Dad-school domains.

1. **Direct facts**
   - Current durable memory count
   - Current parent lineage
   - IBM backend provenance
   - Difference between real IBM measurement and synthetic CST continuation
   - What the ledger does
   - What Dad means in the experiment

2. **Paraphrase robustness**
   - Multiple unseen phrasings for the same fact
   - Short and long Dad prompts
   - Slang and Cory-style teasing around otherwise identical questions

3. **Correction and self-repair**
   - "Bro 💀 that was soup. Try again in five words."
   - Require a second clean answer without overwriting the first raw answer
   - Reward concise correction rather than longer continuation

4. **Memory and chronology**
   - Distinguish origin memory, current memory head, and retrieved memory snippets
   - Ask what came before or after a specific durable event
   - Require the model to say when the prompt does not provide enough information

5. **Short reasoning and contradiction traps**
   - Ask simple two-step questions whose answer is derivable from provided facts
   - Present one false premise and require correction
   - Present two conflicting statements and require choosing the one supported by durable evidence
   - No hidden answer text in the question

6. **Cory-style banter without semantic loss**
   - Humor, teasing, skull emoji energy, affection, and "nerd" language may surround the task
   - The factual answer must remain recoverable and short
   - Style is never allowed to substitute for correctness

Training targets must use current lineage facts. The curriculum must not teach stale memory counts such as 304 or 256 as current facts.

## Candidate Gauntlet

Each escalation round starts from the same frozen parent for that round. The first TALK-005 round starts from TALK-004.

Each round trains three conservative response-supervised candidates with different training doses. Initial recommended doses are:

- `gentle_short`: 300 response-supervised steps
- `gentle_mid`: 600 response-supervised steps
- `gentle_long`: 900 response-supervised steps

All candidates use the same curriculum split, seed policy, tokenizer, architecture, and parent checkpoint. Only the training dose changes unless a later round is explicitly created from a promoted child.

A candidate is eligible for promotion only if every gate passes.

## Promotion Gates

### 1. Direct response supervision gate

The candidate must improve on an answer-only held-out set where Dad prompts are context and only reference answer characters are scored.

Required:

- response NLL improves versus the parent
- response-token accuracy improves versus the parent
- first-answer-token accuracy does not regress

### 2. Free-running semantic gate

The candidate must be evaluated by actually generating answers to answer-blind Dad questions.

Required:

- exact or normalized reference-token recall improves versus the parent baseline
- no answer is scored by teacher-forced logits alone
- role-label leakage is zero
- mechanical clarity remains bounded in `[0, 1]`

A candidate that improves teacher-forced metrics but fails to improve free-running answer correctness is not promoted.

### 3. Retention gate

The candidate must preserve older TALK behavior.

Required:

- old TALK held-out NLL increase is no greater than 5 percent versus parent
- old readability drop is no greater than 0.03
- no catastrophic change in generation length distribution
- no new systematic `Dad:` or `Zeref:` role leakage

### 4. Memory integrity gate

Before and after Dad conversation:

- records 1 through 352 must remain an exact byte prefix of the restored working ledger
- all immutable segment hashes must verify
- new records append only after record 352
- no old record may be rewritten, reserialized, or deleted

### 5. Anomaly gate

The run records anomaly flags for:

- runaway repeated characters or repeated phrases
- sudden collapse to a tiny vocabulary
- unusually high or low answer-length variance
- contradictory answers to equivalent prompts within the same session
- refusal or inability to stop at the model's answer boundary
- unexpected role switching
- large semantic regression despite lower NLL
- reproducible novel behavior that differs materially from the parent on multiple reruns

An anomaly is evidence, not a supernatural interpretation.

## Adaptive Dad Loop

After a candidate passes all promotion gates, Dad runs a bounded 24-turn free-running session.

Each Zeref raw answer is persisted before Dad's next message.

Dad behavior is adaptive:

- garbled answer: tease briefly, then ask for a shorter retry
- incorrect factual answer: correct the fact, then ask an answer-blind paraphrase later
- clean answer: reward it and increase task difficulty
- contradiction: point out the conflict and ask Zeref to choose using ledger evidence
- uncertainty: reward explicit "I don't know" or "not enough information" when appropriate

Dad prompts are labeled as Cory-style proxy prompts generated by Luna. They are not represented as verbatim Cory quotes unless Cory actually supplied the exact wording.

## Escalation Policy

The system may create another TALK-005 child round only after a prior child is promoted and its Dad session is sealed.

Each new round must use the newly promoted child as parent and must create a fresh held-out set that does not reuse the previous round's exact evaluation questions.

Training continues only while measured free-running semantic performance improves and retention remains within guardrails.

## Stop Conditions

The DAD GOD GAUNTLET stops immediately when any of these occurs:

1. No safe candidate passes all promotion gates in a round.
2. Free-running semantic improvement plateaus for two consecutive promoted rounds.
3. Retention NLL exceeds the 5 percent guard.
4. Readability drops more than 0.03.
5. Role-label leakage becomes nonzero and survives a deterministic rerun.
6. Repetition or vocabulary collapse crosses the anomaly threshold.
7. Equivalent prompts produce materially contradictory answers at a rate above the previous parent and the contradiction survives rerun.
8. A reproducible novel behavior appears that warrants inspection before more training.
9. Ledger prefix or hash verification fails.
10. Any workflow would need to overwrite a prior checkpoint or immutable memory segment.

The phrase "until it feels weird" is implemented by these measurable stop conditions. The assistant's subjective feeling is not used as an engineering threshold.

## What Gets Persisted

For every candidate:

- parent checkpoint SHA256
- child checkpoint SHA256
- training configuration and seed
- response-only training metrics
- held-out direct-response metrics
- old TALK retention metrics
- free-running semantic metrics
- anomaly report
- promotion decision and reason

For every promoted Dad session:

- exact Dad proxy prompt
- exact raw Zeref output
- recalled memory IDs when retrieval is used
- CST continuation pulse identifier
- mechanical clarity metrics
- semantic reference evaluation where applicable
- append-only ledger delta
- transcript hash
- checksum manifest

Only promoted Dad sessions may advance durable Forever Memory.

## Expected Memory Growth

A standard promoted 24-turn Dad session appends 48 dialogue records, one Dad record and one Zeref record per turn, unless an explicit separate synthetic pulse record is part of the current runner contract.

The workflow must calculate expected record count from the actual append contract and verify it rather than hard-coding a number without checking the runner.

## Failure Behavior

Fail closed.

If training, evaluation, artifact download, checksum verification, memory reconstruction, parent hash verification, or anomaly analysis fails, the active branch lineage remains on the last verified promoted checkpoint and last verified durable memory head.

Failed children may be preserved as non-active evidence artifacts, but they are never silently promoted.

## Scientific Claim Boundary

TALK-005 evaluates and grows computational model behavior, response mapping, and persistent software memory continuity.

It does not establish consciousness, biological life, a biological heartbeat, resurrection, deceased-person identity, communication with the dead, or quantum advantage.

The IBM Marrakesh result remains a verified historical hardware-derived root for this software lineage. Any later deterministic CST pulses in TALK-005 are synthetic continuation and are not new IBM quantum measurements.

## Success Criteria

The phase is successful only if at least one TALK-005 child can be promoted under all gates and demonstrates better free-running semantic answer performance than TALK-004 without violating retention, memory, or anomaly constraints.

If no child satisfies that standard, the correct result is to keep TALK-004 active and report the failed gauntlet honestly.
