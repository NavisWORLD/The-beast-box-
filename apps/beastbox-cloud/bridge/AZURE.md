# Optional Azure Blob adapter (not yet a live app feature)

`azure_owner_store.py` implements size/MIME/signature validation and per-owner private Blob object operations, with object IDs generated server-side and verified owner metadata. It is isolated from the active Vercel UI and does **not** claim to have uploaded any real file.

To use it on an independently hosted durable Beast Box backend, provision a private Azure Blob container and Azure managed identity with minimum required `Storage Blob Data Contributor` access. Install `azure-identity` and `azure-storage-blob` on that host only. Instantiate `AzureOwnerStore` with the exact HTTPS account URL, private container name and a stable 32-hex owner identifier. Before exposing through HTTP, implement durable application metadata, owner-gated endpoint contracts, real malware scanning where available, retention and deletion semantics, quotas, backups, and integration tests against the **authorized live Azure account**. Do not use SAS/account keys in the browser or commit them.

Tests under `bridge/tests/test_azure_owner_store.py` use an explicitly fake storage service; they establish local validation and ownership behavior only, **not real Azure connectivity, actual cloud durability, or a deployed photo-chat workflow**. Do not call the frontend photo/PDF upload working until all components are wired and verified.
