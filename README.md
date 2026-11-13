# zeref-english-corpus (data branch)

RECORDED corpus: public English written by people, for Zeref's language foundation.
Not Zeref's experience. No model-generated text. Append-only; never force-pushed.

- `zeref-english-001/train.jsonl.gz`: training passages (24 public-domain Project Gutenberg books, header/licence stripped; Taskmaster-1 human dialogue, CC BY 4.0).
- `zeref-english-001/heldout.jsonl`: ~3% held out by stable hash, never trained on.
- `zeref-english-001/manifest.json`: every source with URL, licence, raw sha256 and byte count; screening counts; file sha256s.
- `zeref-english-001/zeref_english_corpus_build.py`: the exact builder.

Taskmaster-1 attribution: Bill Byrne, Karthik Krishnamoorthi, Chinnadhurai Sankar, Arvind Neelakantan, Amit Dubey, Kyu-Young Kim and Andy Cedilnik, Google LLC, CC BY 4.0. Changes: turns joined as A:/B: passages, PII-screened.
