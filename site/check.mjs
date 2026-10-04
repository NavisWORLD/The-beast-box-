/**
 * Compare this directory's JS dyn12 implementation with the committed golden
 * greedy transcript. Requires site/weights/model.safetensors from the pinned release.
 */
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const weightsDir = join(root, "weights");
const golden = JSON.parse(readFileSync(join(root, "golden", "greedy.json"), "utf8"));
const tokenizerGolden = JSON.parse(readFileSync(join(root, "golden", "tokenizer.json"), "utf8"));

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

const modelSha = sha256(join(weightsDir, "model.safetensors"));
const tokSha = sha256(join(weightsDir, "tokenizer.json"));
if (modelSha !== golden.checkpoint_sha256) {
  console.error("model hash mismatch", modelSha);
  process.exit(1);
}
if (tokSha !== golden.tokenizer_sha256) {
  console.error("tokenizer hash mismatch", tokSha);
  process.exit(1);
}

const mod = await import(pathToFileURL(join(root, "rawrphos.js")).href);
const tokenizer = mod.loadTokenizer(JSON.parse(readFileSync(join(weightsDir, "tokenizer.json"), "utf8")));
let failed = 0;
for (const row of tokenizerGolden.cases) {
  const ids = tokenizer.encode(row.text, !!row.add_bos);
  const back = tokenizer.decode(ids);
  if (JSON.stringify(ids) !== JSON.stringify(row.ids) || back !== row.decoded) {
    failed += 1;
    console.error("tokenizer mismatch", JSON.stringify(row.text), ids, row.ids, back, row.decoded);
  }
}
const modelFile = readFileSync(join(weightsDir, "model.safetensors"));
const modelBuffer = modelFile.buffer.slice(modelFile.byteOffset, modelFile.byteOffset + modelFile.byteLength);
const weights = mod.loadWeights(modelBuffer);
for (const row of golden.cases) {
  const ids = tokenizer.encode(row.prompt, true);
  if (JSON.stringify(ids) !== JSON.stringify(row.prompt_ids)) {
    failed += 1;
    console.error("prompt ids mismatch", row.prompt);
    continue;
  }
  const generated = mod.greedyGenerate(weights, ids, row.max_new_tokens, tokenizer.eosId);
  const text = tokenizer.decode(generated);
  if (JSON.stringify(generated) !== JSON.stringify(row.generated_ids) || text !== row.text) {
    failed += 1;
    console.error("greedy mismatch", row.prompt, generated, row.generated_ids, text, row.text);
  } else {
    console.log("MATCH", JSON.stringify(row.prompt), text);
  }
}
if (failed) {
  console.error(`public RAWRPHOS browser check FAIL (${failed})`);
  process.exit(1);
}
console.log("public RAWRPHOS browser check PASS");
