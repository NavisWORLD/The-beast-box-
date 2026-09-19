# Portable product implementation plan

> Use superpowers:subagent-driven-development for independent deliverables and review.

**Goal:** Connect existing runtime, platform packaging and ecosystem adapters.
**Architecture:** Adapt DurableRuntime with explicit host configuration and bounded
JSON interfaces. Preserve QBT and Synapse OS as independently versioned products.
**Tech:** Python, Rust/C++, Kotlin/Chaquopy and supported Apple embedding tools.
**Spec:** docs/PORTABLE_PRODUCT_DESIGN.md

## Global constraints

- Base b6fd43a99475f54f454d4c619d3a7d359757277e; immutable experiments unchanged.
- Python 3.10–3.12 supported; no mandatory cloud keys or trained-model download.
- No hidden hardware jobs, fallback evidence, unbounded authority or key logging.
- No native mobile, physical hardware, OS or production claim without execution.
- Agents own distinct files. Controller owns version, CLI, workflow integration,
  source publication and final release. No agent publishes or modifies history.

## Tasks

- [ ] Desktop and kit: `beastbox/desktop.py`, `kits/BEAST_BOX_COMBINED/` installers,
  `tests/test_portable_install.py`; install a checked wheel in a user venv,
  launch/inspect/restart away from repository and test rejection of changed bytes.
- [ ] Optional inputs: `beastbox/optional_resources.py`, `beastbox/sensor_inputs.py`,
  corresponding tests and `docs/OPTIONAL_INPUTS.md`; return bounded sensor-event-v1
  events and sanitized provenance. Preserve actual provider modes and job receipts.
- [ ] Android: `apps/android/`, packaging workflow fragment and build instructions;
  embed actual Beast Python sources, persistent app-private storage and model
  configuration. Exercise instrumentation or record exact unavailable gate.
- [ ] iOS: `apps/ios/`, packaging workflow fragment and build instructions;
  adapt actual runtime using supported Python embedding if possible; compile and
  run simulator acceptance on CI, keep physical distribution signing unfulfilled.
- [ ] Synapse OS: work on its separate integration branch; add safe user-space
  Beast installation/launch adaptation and test with existing SDK/OS checks.
- [ ] Controller: versioned JSON interface/native examples, ecosystem map, claims,
  final platform CI, package/installer builds and coherent commits/push. Review all
  changed source, fix concrete findings and publish only tested artifact sets.

Each task starts with its failure cases, implements the existing-runtime adapter,
runs focused tests and records commands/results. Whole-product CI is the final
source gate. Review packages include exact changed paths, tests and limitations.
