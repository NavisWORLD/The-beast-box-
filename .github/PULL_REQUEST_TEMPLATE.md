## Summary

Describe exactly what this change does and why it is needed.

## Security / authority boundary

- [ ] This change does not add an unintended host breakout path, credential access path, persistence path, lateral movement path, or arbitrary external-network authority.
- [ ] No live credentials, private keys, tokens, biometric source files, private datasets, or other restricted data are included.
- [ ] Any new network, filesystem, subprocess, cloud, or model authority is explicit, bounded, and documented.

## IP / provenance

- [ ] I have the right to submit every new code/text/media/data item in this change.
- [ ] Third-party material is identified and retains its applicable license/provenance.
- [ ] This change does not silently replace or weaken `LICENSE`, `LICENSE_HISTORY.md`, `IP_NOTICE.md`, `COMMERCIAL_RIGHTS.md`, or `IP_PROVENANCE.md`.
- [ ] Package metadata does not advertise a license inconsistent with the root `LICENSE`.

## Verification

- [ ] Relevant tests pass.
- [ ] `python scripts/security_audit.py` passes.
- [ ] Scientific/mechanism changes include an appropriate control, preflight check, or ablation where practical.
- [ ] Release-impacting changes preserve reproducible build and checksum generation.

## Evidence

List test commands, logs, hashes, screenshots, or other evidence needed to review the change.
