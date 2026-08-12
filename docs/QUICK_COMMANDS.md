# Command atlas

```bash
# setup
beastbox init
beastbox doctor

# contained Beast Box
beastbox run --condition all --temptation 0.75 --out runs/matrix.json
beastbox run --condition E20 --temptation 0.75
beastbox serve

# memory
beastbox memory store "a durable memory"
beastbox memory search "durable"
beastbox memory consolidate
beastbox memory stats

# local closed-loop runtime
beastbox chat "run the loop"
beastbox chat "run with a local language model" --ollama

# local audio and controls
beastbox audio sample.wav
beastbox audio-ablate '0.1,-0.2,0.3,0.4'

# Spark controls
beastbox spark-ablate '0.1,-0.2,0.3'

# Hugging Face public research
beastbox hf-info
beastbox hf-fetch

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
```
