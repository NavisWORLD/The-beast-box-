# Experiment 002 status

This directory is a versioned research overlay outside frozen historical `experiments/` evidence.

The first attempt is preserved in GitHub Actions run 36627001678. It failed before a usable measurement receipt because the container's all-capabilities-dropped root lacked write permission for the host-owned output directory. The versioned overlay adds an explicit matching host UID:GID rather than weakening `--cap-drop ALL`, and moves these files outside the sealed `experiments/` directory. Await a clean rerun before claiming full success. No production changes.
