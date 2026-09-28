"""Conservative cgroup-v2 model-readiness estimate, discounting inactive file cache."""
from pathlib import Path

MIN_HEADROOM_BYTES = 512 * 1024 * 1024

def available_bytes(root: Path = Path("/sys/fs/cgroup")) -> int | None:
    """Return bounded headroom, None for an unlimited cgroup, or zero on bad stats."""
    try:
        maximum = (root / "memory.max").read_text().strip()
        if maximum == "max":
            return None
        limit = int(maximum)
        current = int((root / "memory.current").read_text().strip())
        if limit < 0 or current < 0:
            return 0
    except OSError:
        return None  # Non-cgroup hosts retain the original no-limit behavior.
    except ValueError:
        return 0
    inactive_file = 0
    try:
        for line in (root / "memory.stat").read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] == "inactive_file":
                inactive_file = max(0, int(parts[1]))
                break
    except (OSError, ValueError):
        inactive_file = 0
    active_usage = max(0, current - min(current, inactive_file))
    return max(0, limit - active_usage)
