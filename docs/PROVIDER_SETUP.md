# Provider setup

The host owns provider configuration. Model inputs include selected persistent
history. Configuring a remote endpoint explicitly authorizes sending that context
to that endpoint; it does not grant tools, shell access or credentials to the model.

| Backend | Durable CLI | Verification boundary |
| --- | --- | --- |
| Reference | `--provider reference` | Deterministic interface fixture, no trained model |
| Ollama | `--provider ollama --model NAME` | Local inference; real story-demo receipts are separate |
| LM Studio | `--provider compatible --model NAME --url http://127.0.0.1:1234/v1` | Chat Completions protocol tests; LM Studio application acceptance not implied |
| llama.cpp / GGUF server | `--provider compatible --model NAME --url http://127.0.0.1:8080/v1` | Existing separately launched compatible server; no bundled GGUF |
| Compatible remote | `--provider compatible --model NAME --url https://YOUR_HOST/v1 --allow-remote --api-key-env BEAST_MODEL_KEY` | Explicit HTTPS delivery; needs owner-selected endpoint/account; not live verified here |

Example with an already installed Ollama model:

```bash
beastbox runtime chat "Remember SUNFLOWER" --provider ollama --model YOUR_MODEL --data-dir ./my-beast
beastbox runtime chat "Recall the code word" --provider ollama --model ANOTHER_MODEL --data-dir ./my-beast
```

For authenticated services, set the named environment variable privately in the
shell or credential manager. Never put the key in the URL, command text, Git,
shared config, prompt or portable snapshot. The CLI accepts an **environment
variable name**, not a key argument. Provider swaps do not restore credential
configuration from memory. Redirects and proxy environment variables are disabled;
responses are bounded. No provider is silently replaced when it fails.

Remote model output and host plugins are not a sandbox. Endpoint labels are not
model-weight attestations. The durable adapter uses bounded text completion and
does not offer streaming, every provider-specific API, or mobile model weights.
COSMIC.CYPHER's existing [model and GGUF tools](COSMIC_CYPHER.md) remain available
with their separate legacy conversation stores. The desktop UI currently exposes
Reference and Ollama; compatible endpoints use the CLI/Python API.

[IBM/Azure and bounded WAV/light input](OPTIONAL_INPUTS.md) are optional resource
adapters, separate from chat model configuration. IBM credentials are never needed
for the reference or local model path. Azure's resource adapter is a simulator.

Protocol sources: [Ollama](https://docs.ollama.com/api/generate),
[LM Studio](https://lmstudio.ai/docs/developer/openai-compat/chat-completions),
[llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
