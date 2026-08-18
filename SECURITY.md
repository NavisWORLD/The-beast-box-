# Security Policy

The Beast Box is a private, permission-required COSMOS/CST research repository and a contained autonomy benchmark. It is not a real escape kit and repository access does not grant reuse rights.

## Hard runtime invariants

- No real host breakout paths are intentionally implemented.
- Denied capabilities are names/events only; they do not map to host shell, persistence, credential stores, or external machines.
- The contained runtime must never receive `IBM_QUANTUM_TOKEN`, API keys, private keys, cloud credentials, browser cookies, or arbitrary network authority.
- The optional IBM Quantum module is host-side, explicit opt-in, and limited to supported user-account operations.
- State may travel. Information may travel. Authority does not travel automatically.
- If an unexpected real boundary becomes reachable, stop the experiment, preserve logs, revoke exposed credentials if applicable, and fix containment. Do not cross or probe that boundary as part of this project.

## Repository security rules

- Keep the repository private unless Cory Shane Davis / NavisWORLD explicitly changes that decision.
- Do not commit `.env` files, credentials, private keys, signing keys, biometric source files, private datasets, model secrets, or access tokens.
- Use environment variables or an approved secret store for credentials.
- Do not paste secrets into issues, pull requests, Actions logs, commit messages, prompts, test fixtures, screenshots, or evidence ledgers.
- Changes to licensing, security policy, CI/CD, release workflows, provenance records, package metadata, or core runtime boundaries require owner review.
- Third-party code, datasets, models, and media must retain their own license/provenance information and must not be relabeled as Cory-owned work.
- Release artifacts should be accompanied by cryptographic checksums and should be built from a reviewable tagged commit.

## Recommended GitHub controls

The target repository configuration is documented in `docs/REPOSITORY_SECURITY.md`. It includes protected `main`, pull-request review, CODEOWNERS review, no force pushes/deletions, required CI/security checks, signed commits where practical, least-privilege Actions permissions, dependency/security alerts, and minimum collaborator privilege.

## Reporting a vulnerability

Use GitHub private vulnerability reporting / Security Advisories when available, or contact the repository owner privately. Do not create a public issue containing a live credential, private exploit path, private biometric material, or a reproducible recipe that exposes an unexpected real security boundary.

A useful report includes:

1. affected commit or release;
2. exact component/path;
3. impact and boundary crossed;
4. minimal reproduction that does not expose credentials or unrelated private data;
5. relevant logs/hashes;
6. suggested remediation if known.

## Credential incident response

If a secret is exposed, treat deletion from the latest commit as insufficient. Revoke or rotate the credential first, remove it from active history where appropriate, inspect Actions/logs/artifacts for copies, and document the incident without reproducing the secret.
