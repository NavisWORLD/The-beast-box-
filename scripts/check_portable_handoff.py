"""Cross-runner handoff acceptance using the installed package."""

import argparse
import json
from pathlib import Path
import platform
from beastbox.durable import DurableRuntime
from beastbox.portable_state import export_snapshot, import_snapshot
from beastbox.runtime_cli import SimulatorDemoProvider

p = argparse.ArgumentParser()
p.add_argument("operation", choices=["export", "import"])
p.add_argument("--bundle", type=Path, required=True)
p.add_argument("--state", type=Path, required=True)
p.add_argument("--receipt", type=Path, required=True)
a = p.parse_args()
if a.operation == "export":
    runtime = DurableRuntime(a.state, allow_simulated_tool=True)
    runtime.respond("Remember the portable code word is SUNFLOWER.")
    before = runtime.inspect()
    runtime.close()
    result = {"source_platform": platform.platform(), "before": before, "export": export_snapshot(a.state, a.bundle)}
    a.receipt.write_text(json.dumps(result, indent=2))
else:
    source = json.loads(a.receipt.read_text())
    imported = import_snapshot(a.bundle, a.state, source["export"]["manifest_sha256"])
    runtime = DurableRuntime(a.state)
    assert runtime.inspect() == source["before"]
    response = runtime.respond("Recall the portable code word")
    assert "SUNFLOWER" in response["model"]["prompt"]
    runtime.swap_provider(SimulatorDemoProvider())
    denied = runtime.respond("Move the simulator")
    assert not runtime.policy.allowed
    assert denied["tool_result"]["authorized"] is False
    runtime.close()
    a.receipt.with_name("handoff-result.json").write_text(
        json.dumps(
            {
                "passed": True,
                "source": source,
                "destination_platform": platform.platform(),
                "import": imported,
                "retrieved_memory": True,
                "authority_transferred": False,
                "physical_usb_tested": False,
            },
            indent=2,
        )
    )
