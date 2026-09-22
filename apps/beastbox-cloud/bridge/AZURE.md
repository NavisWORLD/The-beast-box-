# COSMOS Azure Blob integration: explicit read versus offline file adapter

## Implemented in the feature branch

The single-owner Railway bridge supports two **explicit** credential modes in its existing AES-GCM host vault:

- `container_sas` (recommended, also the interpretation of legacy encrypted SAS records).
- `account_key` (Azure Storage account access key; broad Azure permissions; only when the owner specifically selects this mode and privately enters the key).

The current owner-facing operations are **read-only**. `POST /api/connections` with `action=test` checks container metadata and returns sanitized diagnostics. `POST /api/azure-read` requires the authenticated owner, same-origin JSON, one exact `blob_name`, and `read_confirmed=true`. It reads only a `.txt`, `.md`, `.json` or `.csv` object of at most 12 KB from the configured container, returning a SHA-256 digest and bounded text. No recursive scans, automatic memory import, upload, deletes, or quantum jobs occur. The UI requires a **second owner approval** to stage the text as an untrusted temporary attachment for the next chat. A remote model receives the text only when the owner then sends that chat.

A successful container-properties read does **not** attest to a successful object read, chat retrieval, storage writes, or the truth of document contents. The digest proves bytes retrieved in one read, not correctness of facts in those bytes. The raw credential must never enter logs, frontend responses, Git, or model context.

## Separate offline adapter

`azure_owner_store.py` contains independently tested size/MIME/signature checks and owner-prefix upload/download/delete operations. It is **not** wired to any hosted upload or delete route. Its default uses Azure managed identity; the explicit account-key path above does not silently grant those operations. No production upload, backup, deletion, or recovery has been verified.

For a future full file workflow, implement durable metadata indexing, per-owner object access controls, MIME validation, malware scanning, retention/backups and storage quotas; keep upload and delete behind separately authorized actions and cost controls.

## Azure Quantum and Rigetti are not Blob Storage

The storage account key authenticates Blob operations; it does **not** authenticate an Azure Quantum workspace or authorize Rigetti jobs. `beastbox.optional_resources.quantum_event("azure", shots=..., allow_live=True)` includes an *optional*, separately configured Rigetti **QVM simulator** probe for `AZURE_QUANTUM_TARGET=rigetti.sim.qvm`, alongside the preexisting IonQ simulator. It requires the Azure Quantum workspace resource ID, location, and appropriate SDK/identity. Rigetti QPU targets are explicitly rejected in this adapter. Neither QDK nor a job submission endpoint is installed in the tiny production image. All quantum tests use fake SDK objects; no live quantum outcomes were measured.

## Verification and release boundary

Synthetic unit tests, PR CI and browser acceptance establish the software contract only. A real Azure account-key read, owner-chosen object retrieval, and model context response require separate authenticated checks after the compatible Railway backend is deployed, without exceeding the existing $5 monthly hosting ceiling. Do not treat preview READY or a configured key as live Azure evidence.
