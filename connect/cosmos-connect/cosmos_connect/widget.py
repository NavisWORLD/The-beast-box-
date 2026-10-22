"""MCP App view. Renders the tool payload it is given and embeds no sample telemetry."""

DASHBOARD_URI = "ui://cosmos/dashboard.html"

WIDGET_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COSMOS CONNECT</title>
<style>
  :root { color-scheme: dark; --bg:#070711; --panel:#12121f; --line:#2a3348; --text:#e8eaf4; --muted:#9aa3b8; --cyan:#3ee0ff; --violet:#b9a6ff; --amber:#f0c36a; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.45 ui-sans-serif, "Segoe UI", sans-serif; }
  header { padding:16px 16px 8px; border-bottom:1px solid var(--line); background:linear-gradient(90deg, rgba(62,224,255,.12), rgba(167,139,250,.12)); }
  h1 { margin:0; font-size:1.15rem; letter-spacing:.04em; }
  p { margin:6px 0 0; color:var(--muted); }
  main { padding:12px 16px 20px; display:grid; gap:10px; }
  article { border:1px solid var(--line); border-radius:12px; padding:10px 12px; background:var(--panel); }
  h2 { margin:0 0 8px; font-size:.95rem; }
  ul { margin:0; padding-left:18px; }
  li { margin:4px 0; }
  .pill { display:inline-block; margin-left:6px; padding:1px 7px; border-radius:999px; border:1px solid var(--line); font-size:.72rem; letter-spacing:.04em; }
  .live { color:var(--cyan); }
  .historical { color:var(--violet); }
  .implemented { color:var(--text); }
  .unavailable { color:var(--muted); }
  .unverified { color:var(--amber); }
  pre { white-space:pre-wrap; word-break:break-word; background:#0b0b14; border-radius:8px; padding:8px; max-height:280px; overflow:auto; }
  footer { padding:0 16px 16px; color:var(--muted); font-size:.8rem; }
</style>
</head>
<body>
<header>
  <h1>BEAST BOX // COSMOS CONNECT</h1>
  <p id="intro">Waiting for a tool result. This view has no built-in telemetry.</p>
</header>
<main id="out"></main>
<footer>MODEL ≠ MEMORY. MODEL ≠ STATE. MODEL ≠ AUTHORITY. A GitHub success is not live inference.</footer>
<script>
const out = document.getElementById("out");
const intro = document.getElementById("intro");

function pill(state) {
  const span = document.createElement("span");
  span.className = "pill " + ({
    "VERIFIED LIVE": "live",
    "VERIFIED HISTORICAL": "historical",
    "IMPLEMENTED": "implemented",
    "UNAVAILABLE": "unavailable",
    "NOT YET VERIFIED": "unverified"
  }[state] || "unverified");
  span.textContent = state || "NOT YET VERIFIED";
  return span;
}

function article(title) {
  const node = document.createElement("article");
  const heading = document.createElement("h2");
  heading.textContent = title;
  node.appendChild(heading);
  out.appendChild(node);
  return node;
}

function collect(value, prefix, rows) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  if (typeof value.state === "string" && prefix) rows.push({ label: prefix, state: value.state, scope: value.scope || "" });
  Object.keys(value).forEach((key) => {
    if (value[key] && typeof value[key] === "object" && !Array.isArray(value[key])) {
      collect(value[key], prefix ? prefix + "." + key : key, rows);
    }
  });
}

function render(payload) {
  out.replaceChildren();
  if (!payload || typeof payload !== "object") {
    intro.textContent = "No structured tool result was delivered.";
    return;
  }
  intro.textContent = (payload.tool || "tool result") + (payload.ok === false ? " · " + (payload.code || "error") : "");
  const rows = [];
  collect(payload, "", rows);
  if (rows.length) {
    const box = article("Evidence states");
    const list = document.createElement("ul");
    rows.slice(0, 24).forEach((row) => {
      const item = document.createElement("li");
      item.textContent = row.label + " ";
      item.appendChild(pill(row.state));
      if (row.scope) {
        const note = document.createElement("div");
        note.textContent = row.scope;
        item.appendChild(note);
      }
      list.appendChild(item);
    });
    box.appendChild(list);
  }
  if (Array.isArray(payload.architecture_summary)) {
    const box = article("Architecture");
    const list = document.createElement("ul");
    payload.architecture_summary.slice(0, 20).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = (item.id || "component") + " ";
      li.appendChild(pill(item.connect_state));
      list.appendChild(li);
    });
    box.appendChild(list);
  }
  if (typeof payload.original_text === "string") {
    const box = article(payload.excerpt_heading || "Published text");
    const pre = document.createElement("pre");
    pre.textContent = payload.original_text;
    box.appendChild(pre);
  }
  if (payload.live_inference) {
    const box = article("Inference");
    box.appendChild(document.createTextNode("Connector invoked a model: " + String(payload.live_inference.connector_invoked_model === true)));
  }
}

function fromHost(data) {
  if (!data || typeof data !== "object") return;
  if (data.method === "ui/notifications/tool-result") {
    const params = data.params || {};
    render(params.structuredContent || params.result || params);
  }
}

window.addEventListener("message", (event) => fromHost(event.data));
if (window.openai && window.openai.toolOutput) render(window.openai.toolOutput);
try {
  parent.postMessage({ jsonrpc: "2.0", method: "ui/initialize", params: { appInfo: { name: "COSMOS CONNECT", version: "0.1.0" } } }, "*");
} catch (err) {}
</script>
</body>
</html>
"""
