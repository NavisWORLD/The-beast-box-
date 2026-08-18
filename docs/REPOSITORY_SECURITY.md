# THE BEAST BOX — Repository Security Baseline

This document defines the target GitHub security configuration for `NavisWORLD/The-beast-box-`.

## Current verified facts at hardening time

On 2026-08-17 the repository was private, `main` was the default branch, and GitHub reported that `main` was **not protected**. The then-current head commit was also reported as **unsigned**. A recovery/reference branch named `security-baseline-2026-08-17` was created before the hardening changes.

Repository files now provide CODEOWNERS, permission-required licensing, security policy, provenance records, dependency-update configuration, and automated repository-policy checks. GitHub account/repository controls still need to enforce the corresponding server-side rules.

## Required `main` branch rule

Configure a branch protection rule or ruleset for `main` with these goals:

1. Require a pull request before merging for changes made by anyone other than the owner when practical.
2. Require at least one approving review for collaborator-authored changes.
3. Require review from CODEOWNERS for security-, licensing-, release-, provenance-, and core-code changes.
4. Dismiss stale approvals when new commits materially change a pull request.
5. Require conversation resolution before merge.
6. Require status checks to pass before merge, including the normal CI suite and the repository security audit.
7. Require branches to be up to date before merge when appropriate for the workflow.
8. Block force pushes to `main`.
9. Block deletion of `main`.
10. Require signed commits on protected branches when the owner's signing workflow is configured and reliable.
11. Restrict bypass permissions to the minimum necessary owner/admin set.

Do not enable a rule that locks the owner out before a tested signing/recovery path exists.

## Collaborator policy

- Owner/admin: only accounts that actually need administrative control.
- Maintain: only trusted maintainers who need repository-management ability.
- Write: only contributors who need direct branch write access.
- Triage/read: preferred for reviewers who do not need code-write access.
- Remove stale collaborators promptly.
- Do not share one GitHub account or one long-lived personal access token between people.
- Use the smallest-scoped credential possible for automation.

## Owner account protection

- Enable strong two-factor authentication or passkeys on the GitHub owner account.
- Store recovery codes offline in a secure location.
- Review active sessions, SSH keys, deploy keys, GitHub Apps, OAuth apps, personal access tokens, and authorized devices periodically.
- Prefer fine-grained, short-lived credentials over broad classic tokens.
- Keep signing keys and recovery material outside the repository.

## GitHub Actions policy

- Set default workflow token permissions to read-only wherever possible.
- Grant write permissions only at the specific job that needs them.
- Do not make repository secrets available to untrusted pull-request code.
- Review third-party Actions before use and prefer well-known maintainers.
- Pin high-risk third-party Actions to immutable commit SHAs when practical.
- Keep Actions dependencies updated through Dependabot.
- Separate release/publishing jobs from ordinary test jobs.

## Secret and credential protection

Enable the GitHub security features available for the repository/account, including where supported:

- secret scanning;
- push protection;
- dependency graph;
- Dependabot alerts;
- Dependabot security updates;
- private vulnerability reporting / Security Advisories.

Repository policy additionally forbids committing `.env`, private keys, tokens, biometric source files, private datasets, signing material, browser/session credentials, or production secrets.

## Release integrity

For releases:

1. build from a reviewable tag/commit;
2. run tests and the repository security audit first;
3. publish `SHA256SUMS.txt` for release assets;
4. sign tags/releases or use GitHub artifact attestations when an owner-controlled signing/attestation workflow is deliberately configured;
5. never store a private signing key in source control;
6. keep a record of the exact source commit used to build each release.

## Intellectual-property integrity

- `LICENSE`, `LICENSE_HISTORY.md`, `IP_NOTICE.md`, `COMMERCIAL_RIGHTS.md`, and `IP_PROVENANCE.md` are owner-controlled files.
- Package metadata must not advertise an old open-source license after the current permission-required boundary.
- Third-party material must retain its own provenance and license terms.
- CODEOWNERS identifies the owner for all repository content, with explicit coverage of critical files.
- No repository policy can retroactively revoke rights already granted with a valid historical copy.

## Incident procedure

If unauthorized access, a secret leak, malicious commit, unexpected release, or security-boundary failure occurs:

1. preserve evidence and commit/release identifiers;
2. revoke/rotate exposed credentials immediately;
3. suspend compromised automation or collaborators;
4. compare against a known-good commit or the security baseline branch;
5. remove malicious/unauthorized changes through normal recovery procedures;
6. inspect Actions artifacts/logs and release assets for secondary exposure;
7. document what occurred without republishing live secrets;
8. tighten the control that failed.

## Recovery reference

Pre-hardening snapshot branch:

`security-baseline-2026-08-17`

Baseline commit:

`c9e0d136cc16b5d2e4ace432771f8bab16341146`
