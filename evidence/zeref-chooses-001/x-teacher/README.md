# Teacher on X: input hook

Add curated **public** X posts to `inbox.jsonl`, one JSON object per line:

```json
{"post_url": "https://x.com/phera46334652/status/<id>", "posted_at": "2026-10-31T21:00:00Z", "topic": "short topic", "post_text": "the public post text", "narration": "the teacher's explanation of the broadcast", "public": true}
```

Rules:
- Use public posts only. No DMs, tokens or private data.
- Rows without `"public": true` or an `https://x.com/` URL are skipped.
- `scripts/zeref_chooses.py` strips links, other users' @handles (replaced with "someone"), emails and phone-like numbers from the training text.
- Each row becomes framed growing-branch lessons ("The teacher on X explains a broadcast: ...") through the existing reader pipeline. They never enter the pin's mix.
- The site's "Zeref's TV · Teacher on X" strip shows the latest 5 narrated items.
