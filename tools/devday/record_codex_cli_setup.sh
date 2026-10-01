#!/usr/bin/env bash
# Clean, genuinely executed Codex CLI setup; no credentials and no model calls.
set -euo pipefail
out="${1:-$PWD/devday-codex-receipts}"
mkdir -p "$out"
export CODEX_HOME="$out/isolated-codex-home"
mkdir -p "$CODEX_HOME"
transcript="$out/REAL_CLI_TRANSCRIPT.txt"
: > "$transcript"
capture() {
  local display="$1"; shift
  echo "$ $display" | tee -a "$transcript"
  "$@" 2>&1 | tee -a "$transcript"
  echo "" >> "$transcript"
}
echo "BEAST BOX / CORY DAVIS — CODEX CLI SIDE QUEST" | tee -a "$transcript"
echo "Actual CLI commands; a fresh, credential-free workspace." | tee -a "$transcript"
echo "" >> "$transcript"
capture "npm install -g @openai/codex@0.160.0" npm install -g @openai/codex@0.160.0 --no-audit --no-fund
capture "codex --version" codex --version
capture "codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp" codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp
capture "codex mcp list" codex mcp list
capture "codex mcp get openaiDeveloperDocs --json" codex mcp get openaiDeveloperDocs --json
codex mcp list --json > "$out/mcp-list.json"
node - "$out/mcp-list.json" <<'NODE'
const fs=require('node:fs');const p=process.argv[2];const entries=JSON.parse(fs.readFileSync(p,'utf8'));
if (!Array.isArray(entries)) throw new Error('Codex did not return an MCP server list');
const match=entries.find(x=>x.name==='openaiDeveloperDocs');
if (!match || match.url!=='https://developers.openai.com/mcp') throw new Error('Actual Codex CLI did not register docs MCP correctly');
console.log('CODEX_MCP_VERIFIED: server exists at the exact official read-only documentation endpoint');
NODE
printf "CODEX_MCP_VERIFIED: official read-only docs server registered and verified.\n" | tee -a "$transcript"
printf "No ChatGPT login/API key, Codex agent inference, or model-generated code is claimed.\n" | tee -a "$transcript"
