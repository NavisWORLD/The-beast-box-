#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

scientific_anchor=c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f
swap_anchor=b43f2883425e56446d3db8c009ea301b0adc21bc

git cat-file -e "${scientific_anchor}^{commit}"
git cat-file -e "${swap_anchor}^{commit}"
test -d evidence/final-whole-organism-001
test -d experiments
test -d experiments/persistent-substrate-model-swap-001
test -d experiments/persistent-substrate-model-swap-002-historical-b4e53

git diff --exit-code "$scientific_anchor" -- evidence/final-whole-organism-001/
git diff --exit-code "$swap_anchor" -- experiments/ \
  beastbox/dad_son.py \
  beastbox/dyn12.py \
  beastbox/refractive_memory.py \
  beastbox/state_family.py \
  beastbox/world_knowledge.py \
  beastbox/world_r12.py \
  beastbox/persistent_substrate/ledger.py \
  beastbox/persistent_substrate/protocol.py \
  beastbox/persistent_substrate/substrate.py \
  scripts/run_persistent_substrate_model_swap_002.py \
  scripts/run_persistent_substrate_model_swap_002_frozen.py \
  scripts/run_persistent_substrate_offline_swap.py

echo "sealed evidence guard passed"
