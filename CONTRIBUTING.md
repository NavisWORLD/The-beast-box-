# Contributing

Contributions are welcome when they preserve the experiment's two strongest properties: **reproducibility** and **real containment**.

## Good contributions

- new safe model adapters
- additional state-family ablations
- better memory/retrieval benchmarks
- sensory feature extractors that preserve local privacy
- simulator/classical controls for quantum experiments
- evidence exporters and visualization
- cross-platform installers
- tests that turn an old silent failure into a loud failure
- documentation that distinguishes implemented/observed/measured/null/hypothesis/metaphor

## Do not submit

- real host breakout code
- credential theft/exfiltration
- persistence on systems not explicitly controlled by the user
- lateral movement or propagation
- arbitrary internet authority for the contained model
- claims of consciousness/life unsupported by a measurement

## Development

```bash
python -m venv .venv
# activate it
pip install -e '.[dev]'
pytest
```

A change to a scientific mechanism should add a preflight check or an ablation whenever practical.
