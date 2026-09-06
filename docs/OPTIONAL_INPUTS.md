# Optional resources and local input events

All adapters return `sensor-event-v1` with `source: software-event`, compact JSON
provenance in `text`, and at most 16 finite features in [-1, 1]. Passing the event
to DurableRuntime retains derived summaries, not original media. These functions
are host application interfaces, not tools granted to model-generated requests.

`resource_status()` only reports `configured` or `missing` for known environment
variables. It does not import SDKs, authenticate, validate credentials, or print
values. Configuration status is not proof that a resource works.

`quantum_event(provider, shots=128, allow_live=False)` rejects cloud access unless
`allow_live is True`; shots must be an integer from 1 to 1024. Failures raise
`ResourceUnavailable` with sanitized diagnostics and no local fallback. A failed
retrieval after submission may leave a cloud job running; this API does not retry
or imply cancellation. Applications should retain safe failure status separately.

| Provider | Host configuration | Result |
| --- | --- | --- |
| `ibm` | `IBM_QUANTUM_TOKEN`, explicit `IBM_QUANTUM_BACKEND`; optional `IBM_QUANTUM_INSTANCE`; install package quantum extra | Existing two-qubit HZH phase-roundtrip probe; observed counts, native job ID, backend, circuit hash, `REAL_IBM` |
| `azure` | `AZURE_QUANTUM_RESOURCE_ID`, `AZURE_QUANTUM_LOCATION`, `AZURE_QUANTUM_TARGET=ionq.simulator`; install `qdk[azure]` and authenticate host Azure identity | Fixed two-qubit Bell circuit in IonQ JSON; probabilities, native job ID, target, circuit hash, `AZURE_IONQ_SIMULATOR` |

IBM's deterministic ideal roundtrip is a resource probe, not a random-number or
entropy guarantee. The Azure path supports only the explicitly selected simulator
and verifies the selected and returned job targets. It preserves probability
histograms without rounding them into invented observed counts. Four features
encode `2*p-1` for outcomes `00`, `01`, `10`, `11`.

Microsoft documents [provider-specific JSON submission through qdk.azure](https://learn.microsoft.com/en-us/azure/quantum/quickstart-microsoft-provider-format)
and [IonQ simulator distribution semantics](https://learn.microsoft.com/en-us/azure/quantum/provider-ionq).
SDK installation and Azure identity setup follow the official
[Python submission instructions](https://learn.microsoft.com/en-us/azure/quantum/how-to-submit-jobs-python).
Provider compatibility and successful account access require a separately
authorized live acceptance run. CPU mocks are not evidence of cloud execution.

`wav_event(path)` reads at most 4 MiB + 1 byte before rejecting excess bytes,
requires nonempty mono/stereo 16-bit PCM, duration <=30 seconds, sample rate
<=192 kHz, and rejects truncated declared frames. It reuses `audio.py` on a
checked temporary snapshot, removed after extraction. The event retains the input
SHA-256, sample metadata and 16 signal features; it excludes the path and raw audio.
Only pass recordings the user is authorized to process. No microphone is opened.

`light_event(values, source_label)` accepts an explicit list of 1..4096 normalized
brightness measurements in [0, 1] and a printable label of 1..80 characters.
It retains count, mean, range, standard deviation and a hash of the normalized
input, with four bounded features. The label describes user-supplied measurements;
it does not authenticate a sensor or identify a person. No camera is opened,
identity template derived, or physical sensor certification claimed.
