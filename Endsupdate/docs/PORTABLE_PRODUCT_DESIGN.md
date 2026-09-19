# Portable Beast product design

Requested by the owner after verified v0.4.0. Continue from commit
b6fd43a99475f54f454d4c619d3a7d359757277e without changing its release or evidence.

The supported runtime stays Python 3.10–3.12. Native apps, launchers and clients
adapt DurableRuntime; they do not replace it with an unrelated memory engine.
Language interoperability means a versioned JSON interface, not implementation
in every language. No private source, weights, credentials or history is bundled.

Deliverables:

1. EnD installation folder with checked local artifacts, Windows batch and Unix
   launchers, isolated user installation, stable user data location and recovery.
2. Desktop UI over DurableRuntime, retaining model selection, inspect and backup.
3. Optional IBM/Azure configuration and explicit bounded resource submission.
   Credentials stay host-side and are excluded from memory/provenance. Required
   hardware failure never silently becomes simulated evidence.
4. Authorized PCM WAV and light-summary inputs with source-labelled provenance;
   raw media and identity templates are not retained in the memory store.
5. Android on-device runtime adaptation where the available Python embedding
   toolchain permits it, and iOS packaging where Apple toolchains permit it.
   Reference operation is explicitly a fixture; missing local model engines,
   real-device tests and distribution signing are never implied to exist.
6. Explicit link and launcher into the actual Synapse OS Linux distribution,
   preserving its C/C++/Rust SDK and physical-device certification boundary.

Independent source inspection found Synapse OS e48a1e6, QBT c09e1b9 with released
Android/desktop/Rust assets and unsigned iOS builds, and a documentation-only
Cosmic Nova repository. These are separate products until an adapter is exercised.

Persistence means durable retained history under available storage and verified
backups. No finite store or device provides an unconditional forever guarantee.
Apple/Android store identities, user cloud accounts, real sensors and physical
OS hardware are external acceptance resources, not fixtures we can fabricate.

Acceptance: tests for every new data/authority boundary; clean installers outside
source; Python matrix; actual platform builds; native clients; restart/model swap;
fail-closed missing credentials and bad data; source-bound hashes; retained failure
receipts. Publication is allowed only for artifacts whose applicable gates pass.
