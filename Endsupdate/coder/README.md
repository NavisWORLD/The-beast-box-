# Beast Box Coder Workspace

This directory is the owner-controlled workspace for future COSMIC.CYPHER / Beast Box upgrades.

The implementation of the coder remains in `beastbox/cypher/`. This folder is deliberately separate: it is where a selected local model can inspect and modify bounded project files without confusing the coder engine with the work it is editing.

## Start

```bash
beastbox coder doctor
beastbox coder models list
```

Register or discover a local model with the legacy Cypher command or the unified CLI, then:

```bash
beastbox coder chat <alias>
beastbox coder code <alias> "Inspect this workspace and implement the requested change" --workspace coder
```

To allow writes:

```bash
beastbox coder code <alias> "Add a small tested feature" --workspace coder --apply
```

To allow the existing bounded test/build command lane:

```bash
beastbox coder code <alias> "Fix the failing tests" --workspace coder --apply --allow-run
```

The workspace implementation rejects path escape. Existing files are backed up before writes and session activity is audited by the existing COSMIC.CYPHER machinery.

This is not an unrestricted host shell and does not grant credential discovery, privilege escalation, persistence outside the selected workspace, or silent authority expansion.
