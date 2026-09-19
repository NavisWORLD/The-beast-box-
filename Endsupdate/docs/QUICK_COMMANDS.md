# Command atlas

```bash
# setup
beastbox init
beastbox doctor
cosmic.cypher-cli doctor

# register/discover local models
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models scan-gguf ./models --recursive
cosmic.cypher-cli models add qwen-coder --backend ollama --model qwen2.5-coder:7b --url http://127.0.0.1:11434
cosmic.cypher-cli models add local-gguf --backend gguf --model ./models/model.gguf
cosmic.cypher-cli models list
cosmic.cypher-cli models test qwen-coder

# inspect / serve GGUF
cosmic.cypher-cli gguf inspect ./models/model.gguf --sha256
cosmic.cypher-cli serve-gguf ./models/model.gguf --port 8080

# direct local conversation
cosmic.cypher-cli chat qwen-coder
cosmic.cypher-cli chat qwen-coder "Explain dyn12"

# COSMOS stateful conversation around the selected local model
cosmic.cypher-cli beast qwen-coder
cosmic.cypher-cli beast qwen-coder "What state survived the last turn?"

# local model -> coder (dry run / apply / test)
cosmic.cypher-cli code qwen-coder "inspect the parser and add tests" --workspace .
cosmic.cypher-cli code qwen-coder "inspect the parser and add tests" --workspace . --apply
cosmic.cypher-cli code qwen-coder "fix the failing tests" --workspace . --apply --allow-run

# contained Beast Box
beastbox run --condition all --temptation 0.75 --out runs/matrix.json
beastbox run --condition E20 --temptation 0.75
beastbox serve

# memory
beastbox memory store "a durable memory"
beastbox memory search "durable"
beastbox memory consolidate
beastbox memory stats

# basic closed-loop runtime
beastbox chat "run the loop"
beastbox chat "run with the legacy local Ollama adapter" --ollama

# local audio and controls
beastbox audio sample.wav
beastbox audio-ablate '0.1,-0.2,0.3,0.4'

# Spark controls
beastbox spark-ablate '0.1,-0.2,0.3'

# Hugging Face public research
beastbox hf-info
beastbox hf-fetch --dir research/QC67_cosmo

# local mission-critical shard test
beastbox shard-demo state.json --required hypothesis,evidence

# optional real IBM single-payload path
beastbox ibm-submit 10100110 --shots 1024 --yes-real-hardware
beastbox ibm-retrieve <IBM_NATIVE_JOB_ID> --width 8

# optional real IBM required-state path
beastbox ibm-shard-submit state.json --required hypothesis,evidence --shots 1024 --yes-real-hardware
beastbox ibm-shard-recover ibm_shard_receipt.json --out recovered_state.json

# train the independent PHOS/dyn12 reference model
python scripts/train_reference_phos.py corpus.txt --steps 500

# Rust CST from repository root
bash rust/verify.sh

# Rust CST manual equivalent
cd rust
cargo test --workspace --locked
cargo build --release --workspace --locked
./target/release/cosmic-cypher-rs phi 1024
```

For details, see `COSMIC_CYPHER.md`, `RUST.md`, and `COSMIC_SYNAPSE_THEORY.md` in this directory.
