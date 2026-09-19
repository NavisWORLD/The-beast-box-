# Contributing

The Beast Box is a **private, permission-required repository**. Contributions are accepted only with owner authorization and must preserve the experiment's two strongest properties: **reproducibility** and **real containment**.

Repository access or contribution discussion does not grant reuse rights beyond `LICENSE`.

## Good contributions

- new safe model adapters;
- additional state-family ablations;
- better memory/retrieval benchmarks;
- sensory feature extractors that preserve local privacy;
- simulator/classical controls for quantum experiments;
- evidence exporters and visualization;
- cross-platform installers;
- tests that turn an old silent failure into a loud failure;
- documentation that distinguishes implemented/observed/measured/null/hypothesis/metaphor.

## Security requirements

Do not submit:

- real host breakout code;
- credential theft/exfiltration;
- persistence on systems not explicitly controlled by the user;
- lateral movement or propagation;
- arbitrary internet authority for the contained model;
- live credentials, `.env` files, private keys, signing keys, browser/session tokens, or cloud secrets;
- private biometric source files, private datasets, or identifying records unless the owner has explicitly approved the storage boundary;
- claims of consciousness/life unsupported by a measurement.

## IP and provenance requirements

By submitting material for review, you represent that you have the right to provide it for that review. Do not submit third-party code, writing, model weights, datasets, media, or other material and present it as your own or as Cory/NavisWORLD-owned material.

Third-party material must preserve its applicable license, attribution, and provenance. A pull request does not silently change the repository license and does not transfer ownership unless a separate signed agreement says so.

Changes to `LICENSE`, `LICENSE_HISTORY.md`, `IP_NOTICE.md`, `COMMERCIAL_RIGHTS.md`, `IP_PROVENANCE.md`, package-license metadata, security policy, or release workflows require explicit owner review.

## Development

```bash
python -m venv .venv
# activate it
pip install -e '.[dev]'
pytest
python scripts/security_audit.py
```

A change to a scientific mechanism should add a preflight check or an ablation whenever practical.

Before requesting merge, complete the repository pull-request checklist and include test/evidence details sufficient for the owner to review the change.
