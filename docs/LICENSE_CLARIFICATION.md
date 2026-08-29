# License clarification

Status of the historical-MIT vs current-proprietary question:

```text
OWNER LEGAL DECISION REQUIRED
```

This is not an engineering failure. This file does not decide it.

Effective license of current Cory-owned material: **THE BEAST BOX PROPRIETARY SOURCE-AVAILABLE LICENSE v1.0** (root `LICENSE`, 2026-08-17).

Public GitHub visibility is permission to **read** the tree. It is not:

- an OSI open-source license
- permission to copy, modify, redistribute, host, or sell
- permission to train, fine-tune, distill, or evaluate an AI system on this material
- a patent license

| Action | Allowed without extra written permission? |
| --- | --- |
| Read / clone for the purpose access was granted | yes (view) |
| `pip install -e .` locally to inspect the runtime | intended for authorized accessors; redistribution of the package is not granted |
| Modify and publish a fork | no |
| Commercial product incorporation | no |
| Train models on this repo | no |
| Reuse third-party deps (pytest, qiskit, …) | follow **those** licenses |

Historical MIT-licensed copies remain under MIT for those historical copies only (`LICENSE_HISTORY.md`). This file does not revoke those past grants and does not re-license current material as MIT.

Unresolved legal judgment (not invented here): whether every file first published under MIT before 2026-08-17 can still be used under MIT if copied from an old revision. Ask the copyright owner before relying on that.

Do not call this project “open source.”
