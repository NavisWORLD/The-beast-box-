# Teacher distillation (approved pairs)

Talk-to-Beast teachers (My local Ollama, My Hugging Face key, Connected Brain Bay) help
train RAWRPHØS. They are **teachers, not Zeref's voice**. Zeref's voice is RAWRPHØS.

- Visitors' teacher pairs stay **on their device** (`localStorage: beastbox-teacher-pairs-v1`).
- Shared contribution is **opt-in, off by default**, privacy-filtered (secrets/PII), rate-limited
  and stored as `PENDING_REVIEW` (`POST /api/teacher-pairs`). Pending pairs are never trained on.
- Owner pairs (Cory's own Brain Bay, owner session) are `OWNER_AUTO_APPROVED`.
- `approved.jsonl` here (optional) holds manually reviewed pairs with `review_status: APPROVED`.
- `scripts/zeref_teacher_distill.py` adds approved pairs to the chat mix after a persona style
  filter (knowledge yes, teacher personality no), capped at 15% / 300 rows, and the candidate
  still has to pass every 006 gate and the public 14000 chat test.
