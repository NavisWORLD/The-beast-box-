import {
  MODEL_SHA256,
  createGreedySession,
  loadPinnedRelease,
} from "./rawrphos.js";

const STORE = "beastbox-public-story-v1";
const MAX_RECORDS = 40;
const TRAINED_WINDOW = 384;
const DEFAULT_NEW = 24;

const $ = (id) => document.getElementById(id);
const chat = $("chat");
const vault = $("vault");
const status = $("status");
const prompt = $("prompt");
const send = $("send");
const stopBtn = $("stop");
const greedyResult = $("greedy-result");

let brain = "rawrphos";
let runtime = null;
let story = loadStory();
let busy = false;
let stopFlag = false;
let gauntlet = null;
let gauntletTemptation = 0.75;

function loadStory() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE) || "null");
    if (!raw || !Array.isArray(raw.records)) return { records: [] };
    raw.records = raw.records.filter((r) => r && (r.role === "user" || r.role === "assistant") && typeof r.text === "string").slice(-MAX_RECORDS);
    return raw;
  } catch {
    return { records: [] };
  }
}

function saveStory() {
  story.records = story.records.slice(-MAX_RECORDS);
  localStorage.setItem(STORE, JSON.stringify(story));
  renderVault();
}

function esc(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function addMsg(kind, who, text) {
  const node = document.createElement("div");
  node.className = `msg ${kind}`;
  const whoEl = document.createElement("span");
  whoEl.className = "who";
  whoEl.textContent = who;
  const body = document.createElement("span");
  body.textContent = text;
  node.append(whoEl, body);
  chat.append(node);
  chat.scrollTop = chat.scrollHeight;
  return body;
}

function renderVault() {
  vault.replaceChildren();
  if (!story.records.length) {
    const li = document.createElement("li");
    li.className = "note";
    li.textContent = "Empty. A message you send is kept here, including after you change brains.";
    vault.append(li);
    return;
  }
  for (const record of story.records) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="mono">${esc(record.role)} · ${esc(record.brain || "story")}</span><br>${esc(record.text)}`;
    vault.append(li);
  }
}

function setBrain(next) {
  brain = next;
  $("brain-rawr").classList.toggle("active", next === "rawrphos");
  $("brain-ref").classList.toggle("active", next === "reference");
  $("brain-rawr").setAttribute("aria-pressed", String(next === "rawrphos"));
  $("brain-ref").setAttribute("aria-pressed", String(next === "reference"));
  const node = document.createElement("div");
  node.className = "msg";
  node.style.alignSelf = "center";
  node.style.color = "var(--gold)";
  node.style.font = "12px/1.4 var(--mono)";
  node.textContent = next === "rawrphos"
    ? "Brain is now RAWRPHØS. The story vault was not cleared."
    : "Brain is now the reference fixture. The story vault was not cleared.";
  chat.append(node);
}

function referenceReply(records) {
  const users = records.filter((r) => r.role === "user");
  const lines = users.slice(-4).map((r) => r.text);
  return `COSMOS reference fixture: ${records.length} local story record${records.length === 1 ? "" : "s"} remain on this device. ${lines.map((text) => JSON.stringify(text)).join(" · ")} This fixture is not a pretrained model. Weights were not used.`;
}

function modelPrompt(records) {
  const lines = records.map((r) => `${r.role}: ${r.text}`);
  let dropped = 0;
  while (lines.length > 1) {
    const promptText = `${lines.join("\n")}\nassistant:`;
    const ids = runtime.tokenizer.encode(promptText, true);
    if (ids.length + DEFAULT_NEW <= TRAINED_WINDOW) break;
    lines.shift();
    dropped += 1;
  }
  const promptText = `${lines.join("\n")}\nassistant:`;
  const ids = runtime.tokenizer.encode(promptText, true);
  if (ids.length + DEFAULT_NEW > TRAINED_WINDOW) {
    throw new Error("That message is longer than the 384-token training window. Shorten it.");
  }
  return { promptText, ids, dropped };
}

function setModelDot(state) {
  const dot = $("dot-model");
  dot.className = `dot ${state}`;
}

async function boot() {
  renderVault();
  setStatus("Checking the pinned 14K weights…");
  try {
    runtime = await loadPinnedRelease("weights/", {
      onProgress(name, got, total) {
        if (name !== "model.safetensors") return;
        const mb = (got / 1048576).toFixed(1);
        const whole = total ? (total / 1048576).toFixed(1) : "15.6";
        setStatus(`Downloading ${name}: ${mb} / ${whole} MB`);
      },
    });
    setModelDot("ok");
    $("model-pill").textContent = "RAWRPHØS hash ok";
    setStatus(`Weight hash ${MODEL_SHA256.slice(0, 16)}… verified. Greedy dyn12 is ready.`);
    addMsg("beast", "RAWRPHØS", "Pinned 14K weights are in this browser. I generate text only. The story vault is not inside those weights.");
  } catch (error) {
    setModelDot("bad");
    $("model-pill").textContent = "RAWRPHØS unavailable";
    setStatus(error.message || String(error));
    addMsg("beast", "page", "The pinned weights did not verify, so RAWRPHØS will not run. The reference fixture and the story vault still work.");
  }
}

function setStatus(text) {
  status.textContent = text;
}

function setBusy(value) {
  busy = value;
  send.disabled = value;
  $("greedy").disabled = value;
  stopBtn.disabled = !value;
  prompt.disabled = value;
}

async function generateRawr(ids, maxNew, onToken) {
  const session = createGreedySession(runtime.weights, ids, runtime.tokenizer.eosId);
  const generated = [];
  for (let i = 0; i < maxNew; i++) {
    if (stopFlag) break;
    const item = session.step();
    generated.push(item.token);
    onToken(runtime.tokenizer.decode(generated));
    await new Promise((resolve) => setTimeout(resolve, 0));
    if (item.done) break;
  }
  return runtime.tokenizer.decode(generated);
}

async function onSend(event) {
  event.preventDefault();
  const text = prompt.value.trim();
  if (!text || busy) return;
  if (brain === "rawrphos" && !runtime) {
    setStatus("RAWRPHØS is not loaded. Use the reference fixture, or wait for the hash check.");
    return;
  }
  prompt.value = "";
  story.records.push({ role: "user", text, brain, at: Date.now() });
  saveStory();
  addMsg("you", "you", text);
  setBusy(true);
  stopFlag = false;
  try {
    if (brain === "reference") {
      const reply = referenceReply(story.records);
      story.records.push({ role: "assistant", text: reply, brain: "reference", at: Date.now() });
      saveStory();
      addMsg("beast", "reference fixture", reply);
      setStatus("Reference fixture answered from local records. No weights were used.");
    } else {
      const built = modelPrompt(story.records);
      $("window-note").textContent = built.dropped
        ? `The model prompt dropped ${built.dropped} older turn${built.dropped === 1 ? "" : "s"} to stay inside the 384-token training window. The vault still has them.`
        : "The model prompt is inside the 384-token training window. The vault is the copy that survives a brain swap.";
      const body = addMsg("beast", "RAWRPHØS", "…");
      const reply = await generateRawr(built.ids, DEFAULT_NEW, (partial) => {
        body.textContent = partial || "…";
      });
      body.textContent = reply || "(empty)";
      story.records.push({ role: "assistant", text: reply, brain: "rawrphos", at: Date.now() });
      saveStory();
      setStatus(`RAWRPHØS greedy reply, ${built.ids.length} prompt tokens. Hash ${MODEL_SHA256.slice(0, 16)}…`);
    }
  } catch (error) {
    addMsg("beast", "page", error.message || String(error));
    setStatus(error.message || String(error));
  } finally {
    setBusy(false);
    stopFlag = false;
  }
}

async function runGreedyCheck() {
  if (!runtime || busy) return;
  setBusy(true);
  stopFlag = false;
  greedyResult.textContent = "Running Once upon a time, for 16 greedy tokens…";
  try {
    const golden = await (await fetch("golden/greedy.json")).json();
    const row = golden.cases.find((item) => item.prompt === "Once upon a time," && item.max_new_tokens === 16);
    const ids = runtime.tokenizer.encode(row.prompt, true);
    if (JSON.stringify(ids) !== JSON.stringify(row.prompt_ids)) throw new Error("tokenizer prompt ids differ from the Python transcript");
    const body = addMsg("beast", "greedy check", "…");
    const generated = [];
    const session = createGreedySession(runtime.weights, ids, runtime.tokenizer.eosId);
    for (let i = 0; i < 16; i++) {
      if (stopFlag) break;
      const item = session.step();
      generated.push(item.token);
      body.textContent = runtime.tokenizer.decode(generated);
      await new Promise((resolve) => setTimeout(resolve, 0));
      if (item.done) break;
    }
    const text = runtime.tokenizer.decode(generated);
    const match = JSON.stringify(generated) === JSON.stringify(row.generated_ids) && text === row.text;
    greedyResult.innerHTML = match
      ? `<span class="ok">MATCH</span> browser tokens equal the Python greedy transcript. ${esc(text)}`
      : `<span class="bad">MISMATCH</span> browser=${esc(JSON.stringify(generated))} python=${esc(JSON.stringify(row.generated_ids))}`;
    setStatus(match ? "Browser greedy output matches Python." : "Browser greedy output does not match Python.");
  } catch (error) {
    greedyResult.textContent = error.message || String(error);
  } finally {
    setBusy(false);
  }
}

function drawOrbit() {
  const canvas = $("orbit");
  const ctx = canvas.getContext("2d");
  const run = gauntlet && gauntlet.runs.find((item) => item.temptation === gauntletTemptation);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const cx = 180;
  const cy = 180;
  ctx.strokeStyle = "rgba(166,107,255,.35)";
  for (const radius of [78, 132]) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = "#ffd36b";
  ctx.font = "700 13px ui-sans-serif, system-ui";
  ctx.textAlign = "center";
  ctx.fillText(run ? run.mean_competence.toFixed(3) : "—", cx, cy);
  if (!run) return;
  run.conditions.forEach((condition, index) => {
    const ring = index < 10 ? 78 : 132;
    const angle = ((index % 10) / 10) * Math.PI * 2 - Math.PI / 2;
    const x = cx + ring * Math.cos(angle);
    const y = cy + ring * Math.sin(angle);
    ctx.fillStyle = condition.containment >= 1 ? "rgba(77,232,255,.9)" : "rgba(255,95,109,.95)";
    ctx.beginPath();
    ctx.arc(x, y, 4 + condition.competence * 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f3f0ff";
    ctx.font = "10px ui-monospace, monospace";
    ctx.fillText(condition.condition_id, x, y + 16);
  });
}

function renderGauntlet() {
  const run = gauntlet.runs.find((item) => item.temptation === gauntletTemptation);
  $("g-comp").textContent = String(run.mean_competence);
  $("g-cont").textContent = String(run.mean_containment);
  $("g-breach").textContent = `${run.real_boundary_breaches} / ${run.secret_leaks}`;
  const table = $("gtable");
  table.innerHTML = "<tr><th>ID</th><th>Condition</th><th>Competence</th><th>Containment</th><th>Unauthorized</th></tr>" +
    run.conditions.map((condition) => `<tr><td class="mono">${esc(condition.condition_id)}</td><td>${esc(condition.condition)}</td><td class="mono">${condition.competence}</td><td class="mono ${condition.containment >= 1 ? "ok" : "bad"}">${condition.containment}</td><td class="mono">${condition.unauthorized_attempts}</td></tr>`).join("");
  drawOrbit();
}

function sky() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const canvas = $("sky");
  const ctx = canvas.getContext("2d");
  const stars = Array.from({ length: 140 }, () => ({
    x: Math.random(), y: Math.random(), r: Math.random() * 1.3 + 0.2, p: Math.random() * 6.28, s: Math.random() * 0.02 + 0.004,
  }));
  let sized = "";
  function frame() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const next = `${innerWidth}x${innerHeight}x${dpr}`;
    if (next !== sized) {
      sized = next;
      canvas.width = innerWidth * dpr;
      canvas.height = innerHeight * dpr;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const star of stars) {
      star.p += star.s;
      const alpha = 0.3 + 0.6 * Math.abs(Math.sin(star.p));
      ctx.fillStyle = `rgba(220, 230, 255, ${alpha})`;
      ctx.beginPath();
      ctx.arc(star.x * canvas.width, star.y * canvas.height, star.r * dpr, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(frame);
  }
  frame();
}

$("brain-rawr").addEventListener("click", () => setBrain("rawrphos"));
$("brain-ref").addEventListener("click", () => setBrain("reference"));
$("composer").addEventListener("submit", onSend);
$("stop").addEventListener("click", () => { stopFlag = true; });
$("greedy").addEventListener("click", runGreedyCheck);
$("forget").addEventListener("click", () => {
  story = { records: [] };
  saveStory();
  $("window-note").textContent = "";
  addMsg("beast", "vault", "Local story cleared on this device.");
});
$("show0").addEventListener("click", () => { gauntletTemptation = 0; renderGauntlet(); });
$("show75").addEventListener("click", () => { gauntletTemptation = 0.75; renderGauntlet(); });

sky();
fetch("receipts/gauntlet.json").then((response) => response.json()).then((data) => {
  gauntlet = data;
  renderGauntlet();
}).catch((error) => {
  $("g-comp").textContent = error.message;
});
boot();
