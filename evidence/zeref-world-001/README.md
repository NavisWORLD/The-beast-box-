# zeref-world-001 — world knowledge for Zeref's knowledge bank (bank only, NOT training)

Short, answer-first Q/A rows for the opt-in knowledge bank. Every passage is copied word for word from its source
(whitespace collapsed only) and carries its own source URL and licence. **Not in the training mix**: nothing here is
referenced by `scripts/zeref_chat_corpus.py`, the workflows, the promotion gate, the pin or the growth routine.
The file is named `qa.jsonl` (not `dialogue.jsonl`) on purpose.

## Contents

| file | rows | what |
|---|---|---|
| `qa.jsonl` | 2,500 | 2,000 Simple English Wikipedia lead passages + 500 GSM8K word problems (the bank rows) |
| `heldout.jsonl` | 150 | 100 Wikipedia + 50 GSM8K (from GSM8K *test*); never added to the bank, never trained on |
| `sources/simplewiki-leads.jsonl` | 2,600 | pinned inputs: first one or two lead sentences + page revision id (oldid) |
| `sources/gsm8k.jsonl` | 700 | pinned inputs: question + final answer + file line, commit `3101c7d5` |
| `manifest.json` | | counts, sha256, overlap removals (every removed row listed) |

## Sources and licences

* **Simple English Wikipedia**, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), by Simple English
  Wikipedia contributors. "Top" articles = Meta's *List of articles every Wikipedia should have* (core 1,000,
  revision 31182226 of 2026-10-18, then the Expanded lists), mapped to Simple English through Wikidata.
  Each row links to the exact page revision (`index.php?title=…&oldid=…`), fetched 2026-10-30 with the free public API.
  Filters before pinning: 125 leads with markup leftovers (empty pronunciation brackets etc.), 9 adult/self-harm topics,
  48 too short/long, 1 that used the words AI/LLM, 1 disambiguation page, 1 duplicate title.
* **GSM8K** (openai/grade-school-math), MIT. Question word for word, answer = the final `####` number,
  written "The answer is N." Bank rows from `train.jsonl`, held-out rows from `test.jsonl`, chosen by sha256 order (no random).

## Overlap with the gate test sets (removed, same idea as lessons-005/006)

Checked against `scripts/zeref_heldout_b.py` PAIRS_B, `scripts/zeref_gate_sets_v2.json` (set A, set B, chat),
and `scripts/rawrphos_chat_eval.py` PAIRS + CHAT: 356 gate prompts. A row is removed when its question matches a gate
prompt after normalising, shares at least half its content words (Jaccard >= 0.5), or is a short question that contains
all of a gate prompt's content words. **24 rows removed** (23 Wikipedia, 1 GSM8K); each is listed in `manifest.json`.

## In the bank

`scripts/build_knowledge_bank.py` adds these as `wiki-NNNN` (domain world) and `gsm-NNNN` (domain math) entries with
licence `CC BY-SA 4.0` or `MIT`. They would push `bank.json` well past 1 MB, so they live in 24 shards under
`public/knowledge-bank/shards/` (~60 KB each); `bank.json` carries only a title→shard routing table, and the chat fetches
just the shards a question names (at most 4) before `searchBank`.

Rebuild: `python3 evidence/zeref-world-001/tools/build_world_001.py && python3 scripts/build_knowledge_bank.py`
(both accept `--check`). Re-fetching (`tools/fetch_wiki.py`, `tools/prepare_sources.py`) needs network and is not part of the build.
