# Cross-platform research: numerical parity only

Python is the existing complete fly experiment, model, learner and renderer. The independent C++17 and Rust programs here implement just one 42-node numerical neural-step loop and the twelve-scalar dyn12 reference state. They are **not** full native fly implementations. The Python executable experiment, fixtures, and tests must be synced separately from the existing verified local archive before the whole research project is runnable from a fresh clone.

Windows launchers use Python, g++, Cargo and ffmpeg when present; they do not install those dependencies. The numerical fixture has 42x42 weights, 42 stimulus values, 42 initial state values, 12 initial dyn12 values, and step count and offset. Inputs use a plain UTF-8 whitespace-separated format. Outputs are JSON vectors. No private raw bio recording is included. FlyWire-derived data remains subject to CC BY-NC 4.0. Do not claim a biological or quantum performance advantage.

This isolated native interface is one partial source delivery step. Source archive upload, CI, and integration remain open gates.
