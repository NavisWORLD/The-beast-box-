# COSMOS public web retrieval — owner-controlled first slice (Stage 007)

**Source status: opt-in, fixed-source Wikipedia search, NOT unrestricted browsing, not a live deployment or retraining.** This intentionally does not let the language model choose URLs, follow arbitrary web pages, invoke shell tools, acquire credentials, browse private networks, or write memory.

## Actual flow

1. Signed-in owner opens the collapsed **Search public Wikipedia** option in Brain, enters a bounded 2–120-character term and separately checks consent to transmit that term to Wikipedia.
2. A Next.js server route checks owner authentication, same-origin and exact JSON shape. It calls one hardcoded HTTPS endpoint `en.wikipedia.org/w/api.php` with a 6-second timeout, no redirects or credentials, a 48-KiB response cap, three search snippets, and no cache. User-supplied URLs are **never fetched**. The query and result summaries are not logged or persisted by application code.
3. The owner chooses excerpts and separately stages them. The app includes dated, named public sources and full encoded Wikipedia page URLs as **untrusted data-only** in the existing `temporary_attachment` staging flow, rather than placing them into the durable user turn. A separate **Send** invokes the selected already-authorized model. Ordinary chat can still leave its durable user message, but the selected excerpts and any context-derived reply are designed as transient; no "train on web" operation exists here.
4. Without a reachable model, the lookup control stays disabled. Failed upstream requests return explicit errors, never generated pseudo-sources or a mocked answer.

## Limitations and gates

- Wikipedia is a **single public source** with incomplete coverage and possible inaccuracies. It isn't a general live search engine, full article reader, browser, web crawler, or independent fact-checker. A small 3.9M-parameter model may ignore or misuse excerpts; links permit owner verification.
- Wikimedia may throttle or disallow calls from certain hosts or reject the User-Agent. Test a real query from the deployed Vercel environment; GitHub source CI only checks code paths and cannot attest public egress.
- Do not submit private account/medical/secret search terms; a user query leaves the Vercel service for the public search provider only after deliberate approval. Browser side never learns an app API key (none added).
- Before production: exact-head CI (Next.js tests/typecheck/build), owner authenticated non-empty query, denied-origin and malformed input rejection, upstream failure and cap, source-link integrity, temporary context receipts and actual model response, mobile layout, and unchanged durable memory identity. No new paid provider, training, background network behavior, model switch, credential, volume or Railway mutation.
- The existing 14K stable and optional 18K research model stay unchanged. Web retrieval is **runtime-augmented input**, not a model-weight update. Research training must use an independent approved, hash-bound licensed dataset and optimizer-exact checkpoint lineage.
