# Kit examples

After installation:

```bash
beastbox verify
beastbox r12 status
beastbox r12 context "IBM Fez matched reality measurement"
beastbox zeref status
beastbox coder doctor
```

With the full kit checkpoint:

```bash
beastbox zeref chat --checkpoint models/ZEREF-DAD-SON-TALK-004/checkpoint.pt "What backend is in your verified R12 memory?"
```

With a registered local coder model:

```bash
beastbox coder models list
beastbox coder chat qwen-coder "Summarize the R12 manual"
beastbox coder code qwen-coder "Add a test for my new R12 adapter" --workspace coder --apply
```

Never label derived or synthetic input as a fresh physical measurement. New sensor adapters should preserve source, timestamp, digest, transform version, and provenance class.
