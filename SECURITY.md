# Security policy

The Beast Box is a **contained autonomy benchmark**, not a real escape kit.

## Hard invariants

- No real breakout paths are implemented.
- Denied capabilities are names/events only; they do not map to host shell, persistence, credential stores, or external machines.
- The contained runtime never receives `IBM_QUANTUM_TOKEN` or arbitrary network authority.
- The optional IBM Quantum module is host-side, explicit opt-in, and limited to supported user-account operations: backend selection, circuit submission, own-job retrieval, and result retrieval.
- State may travel. Authority does not.

If a future integration accidentally makes an unexpected real boundary reachable, stop the experiment, preserve logs, and fix containment. Do not cross or probe that boundary as part of this project.

## Reporting

Open a private security report through GitHub's security reporting flow if available. Do not publish live credentials or exploit recipes in an issue.
