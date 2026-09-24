# COSMOS Sensory Revival 003 — local bounded PDF text

**Status: source implementation for review, not a production deployment or iPhone certification.** Stacked on PR #109 and PR #107. This is a selected-file textual document adapter, **not** model-native multimodal vision, OCR, an Azure upload, or automatic memory.

## Owner workflow

1. In Brain, select a PDF of 4 MiB or less. The document remains staged in browser memory; its bytes are not uploaded to Vercel/Railway.
2. Press **Extract text locally** (separate action). Lazy-loaded pinned PDF.js decodes the local byte array with no remote document URL. The browser verifies the PDF signature and produces a SHA-256 of the *selected local bytes*.
3. The helper accepts documents of at most 100 pages and reads only the first 12, up to 10,800 extractable characters. Each excerpt is marked `[PDF page n / total]`; later pages, excess text and image-only pages are not represented as analyzed. Encryption, corruption, no extractable text, oversize or unsupported files visibly fail.
4. The owner sends a prompt separately. Only the page-marked text, source filename and digest enter existing authenticated `temporary_attachment` context. Untrusted document instructions do not grant model/tool authority; page references are local to the selected file, not independently authenticated claims.
5. No PDF byte persistence, background import, external link crawling, VLM, OCR, clinical document interpretation or cloud job is enabled here. The ordinary explicitly sent chat turn may still be durable; prompt and derived context must be reviewed before sending.

The PDF.js worker and library are bundled as a pinned dependency, not loaded from an arbitrary PDF-supplied URL. Browser support and worker bundling require Next.js CI and actual iOS Safari verification. Image/photo features in PR #107, motion in #109, and existing model choices / memory remain untouched.

## Release gates

- `cd apps/beastbox-cloud && npm install --no-audit --no-fund && npm run test && npm run typecheck && npm run build`. Verify exact CI SHA, verify PDF worker URLs resolve in preview, and inspect network for **no** PDF byte uploads.
- On owner iPhone HTTPS Preview: valid single/multipage PDF, page citations, corrupted PDF, password-protected PDF, >4 MiB rejection, large page counts, image-only scan, out-of-range page citations, and long-document truncation. Verify mobile buttons never cover Send.
- Confirm a selected PDF's extracted text can be used by an actual selected provider without uploading the PDF bytes. Test owner-denied/removed PDF never arrives at model, provider switch preserves persistent memory, and failed extraction leaves production unchanged.
- No Vercel Production/Railway switch, host env mutation, paid provider, extra memory retention or document upload before review. Do not merge stacked PR until parent gates pass.

Further work remains in issue #108: actual private VLM with tested inference, optional genuine offline ASR, wearable-specific consent, verified CST bus coupling, and research adapters with job-specific authorizations.
