"""Midnight command surface. The page renders the same tool payloads the MCP server returns."""

from __future__ import annotations

import html
import json

from .evidence import RESEARCH, WORKFLOWS, SourceBook, call_tool

PILL_CLASS = {
    "VERIFIED LIVE": "live",
    "VERIFIED HISTORICAL": "historical",
    "IMPLEMENTED": "implemented",
    "UNAVAILABLE": "unavailable",
    "NOT YET VERIFIED": "unverified",
}


def render_home(book: SourceBook) -> str:
    status, _ = call_tool("beastbox_get_status", {}, book)
    architecture, _ = call_tool("beastbox_get_architecture", {}, book)
    models, _ = call_tool("beastbox_list_models", {}, book)
    sensory, _ = call_tool("beastbox_get_sensory_status", {}, book)
    sha = (status.get("github_main") or {}).get("sha")
    parts = [
        _page_open("BEAST BOX // COSMOS CONNECT"),
        "<header>",
        "<p class='kicker'>COSMOS CONNECT · public evidence</p>",
        "<h1>BEAST BOX // COSMOS CONNECT</h1>",
        "<p class='lede'>A controlled read of Cory Davis’s existing COSMOS. This page does not replace the runtime, run a model, or collect sensor data.</p>",
        "<ul class='invariants'>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in status.get("invariants", []))
        + "</ul>",
        f"<p class='meta'>Retrieved {_esc(status.get('timestamp'))}. Values below are the tool results, not a sample dashboard.</p>",
        "</header>",
        "<nav>",
        "<a href='#architecture'>Architecture</a>",
        "<a href='#revisions'>Revisions</a>",
        "<a href='#models'>Models</a>",
        "<a href='#health'>Health</a>",
        "<a href='#research'>Research</a>",
        "<a href='#senses'>Senses</a>",
        "<a href='#integration'>Integration</a>",
        "<a href='/install'>Install</a>",
        "</nav>",
        "<main>",
        _section("health", "Deployment health", _health_body(status)),
        _section("revisions", "Repository revisions", _revision_body(status)),
        _section("architecture", "Architecture", _architecture_body(architecture)),
        _section("models", "Model inventory", _models_body(models)),
        _section("research", "Research receipts", _research_body(sha)),
        _section("senses", "Sensor capabilities", _sensory_body(sensory)),
        _section("integration", "Integration status", _integration_body(status)),
        _section("ci", "GitHub verification", _ci_body()),
        "</main>",
        "<footer>Owner connection disabled. Public tools send no Railway token. GitHub success is source verification only.</footer>",
        "</body></html>",
    ]
    return "".join(parts)


def render_install(local_mcp: str) -> str:
    tools = [
        "beastbox_get_status",
        "beastbox_get_architecture",
        "beastbox_list_models",
        "beastbox_get_research",
        "beastbox_get_sensory_status",
        "beastbox_get_ci",
        "beastbox_search_mentions",
        "beastbox_open_dashboard",
    ]
    description = (
        "Connects ChatGPT to Cory Davis’s existing COSMOS architecture, verified engineering evidence, "
        "and authorized Beast Box capabilities."
    )
    body = [
        _page_open("Install · BEAST BOX // COSMOS CONNECT"),
        "<main class='install'>",
        "<article class='card'>",
        "<p class='kicker'>Personal plugin · private until you share it</p>",
        "<h1>BEAST BOX // COSMOS CONNECT</h1>",
        f"<p>{html.escape(description)}</p>",
        "<dl>",
        f"<dt>Local MCP endpoint</dt><dd><code>{html.escape(local_mcp)}</code></dd>",
        "<dt>Sites MCP URL</dt><dd><code>https://&lt;your-private-site&gt;/mcp</code></dd>",
        "<dt>Public tool authorization</dt><dd>None. No Railway token.</dd>",
        "<dt>Owner tools</dt><dd>Disabled. Calls return OWNER_CONNECTION_DISABLED and do not reach the bridge.</dd>",
        "<dt>Capture</dt><dd>Camera, microphone, and biometric collection stay off.</dd>",
        "</dl>",
        "<h2>Read-only tools</h2><ul>",
        "".join(f"<li><code>{html.escape(name)}</code></li>" for name in tools),
        "</ul>",
        "<h2>Remaining authorization</h2><ol>",
        "<li>Open ChatGPT Sites and link this project. <code>.openai/hosting.json</code> has no project id until Sites provisions one.</li>",
        "<li>Save a version, review it, then deploy with access limited to you.</li>",
        "<li>Point the personal plugin at <code>https://&lt;site&gt;/mcp</code>. Do not use a desktop-only stdio server.</li>",
        "<li>In a fresh ChatGPT conversation, call the read-only tools and confirm the revision matches GitHub.</li>",
        "<li>Leave owner tools disabled until a server-side scoped secret exists and the backup, isolated restore, deployment, and live acceptance records exist.</li>",
        "</ol>",
        "<p class='meta'>This environment has no ChatGPT session, so the Site URL and installation dialog are not claimed here.</p>",
        "<p><a href='/'>Back to evidence</a></p>",
        "</article></main></body></html>",
    ]
    return "".join(body)


def _health_body(status: dict) -> str:
    rows = [
        _fact("Public release", status.get("release") or {}),
        _fact("Public website", status.get("frontend") or {}),
        _fact("Backend readiness", status.get("backend_readiness") or {}),
        _fact("Backend activation", status.get("backend_activation") or {}),
        _fact("Live inference", status.get("live_inference") or {}),
        _fact("Deployment identity", status.get("deployment_identity") or {}),
    ]
    bridge = status.get("private_bridge_unauthenticated") or {}
    rows.append(_fact("Unauthenticated /api/orbit", bridge.get("orbit") or {}))
    rows.append(_fact("Unauthenticated /api/models", bridge.get("models") or {}))
    return "".join(rows)


def _revision_body(status: dict) -> str:
    github = status.get("github_main") or {}
    release = status.get("release") or {}
    return "".join(
        [
            _fact("GitHub main", github),
            f"<p>SHA <code>{_esc(github.get('sha'))}</code></p>",
            f"<p>Subject {_esc(github.get('subject'))}</p>",
            f"<p>Release marker <code>{_esc(release.get('source_marker'))}</code></p>",
            f"<p>{_esc((status.get('deployment_identity') or {}).get('scope'))}</p>",
        ]
    )


def _architecture_body(payload: dict) -> str:
    if payload.get("ok") is False:
        return f"<p class='error'>{_esc(payload.get('code'))}: {_esc(payload.get('message'))}</p>"
    items = []
    for component in payload.get("components") or []:
        items.append(
            "<article class='module'>"
            f"<h3>{_esc(component.get('id'))} {_pill(component.get('connect_state'))}</h3>"
            f"<p>Repository status {_esc(component.get('repository_status'))}</p>"
            f"<p>{_esc(component.get('boundary'))}</p>"
            "</article>"
        )
    rule = payload.get("manifest_status_rule")
    return f"<p>{_esc(rule)}</p><div class='modules'>{''.join(items)}</div>"


def _models_body(payload: dict) -> str:
    if payload.get("ok") is False:
        return f"<p class='error'>{_esc(payload.get('code'))}: {_esc(payload.get('message'))}</p>"
    rows = []
    for item in payload.get("identities") or []:
        rows.append(
            "<li>"
            f"<strong>{_esc(item.get('name'))}</strong> {_pill(item.get('source_state'))} "
            f"<span>{_esc(item.get('kind'))}</span> · live {_pill(item.get('live_production'))}"
            f"<div>{_esc(item.get('detail'))}</div></li>"
        )
    verification = payload.get("live_production_verification") or {}
    return (
        f"<p>Live production inventory {_pill(verification.get('state'))}</p>"
        f"<ul class='plain'>{''.join(rows)}</ul>"
        "<p>Historical experiment identities load through the model tool with include_historical, from the published swap report.</p>"
    )


def _research_body(sha: object) -> str:
    buttons = []
    for experiment, path in RESEARCH.items():
        link = ""
        if isinstance(sha, str):
            url = f"https://github.com/NavisWORLD/The-beast-box-/blob/{sha}/{path}"
            link = f" <a href='{html.escape(url, quote=True)}'>source</a>"
        buttons.append(
            "<li>"
            f"<button type='button' data-experiment='{html.escape(experiment, quote=True)}'>{html.escape(experiment)}</button>"
            f"{link}<div class='receipt' hidden></div></li>"
        )
    script = """
<script>
document.querySelectorAll("[data-experiment]").forEach((button) => {
  button.addEventListener("click", async () => {
    const slot = button.parentElement.querySelector(".receipt");
    slot.hidden = false;
    slot.textContent = "Retrieving the published file…";
    const response = await fetch("/api/call", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name: "beastbox_get_research", arguments: {experiment: button.dataset.experiment}})
    });
    const payload = await response.json();
    slot.textContent = "";
    const state = document.createElement("div");
    state.textContent = (payload.code || payload.state || "") + " · " + (payload.source_revision || "");
    const pre = document.createElement("pre");
    pre.textContent = payload.original_text || payload.message || "";
    slot.append(state, pre);
  });
});
</script>
"""
    return (
        "<p>Each receipt is fetched from the repository when opened. The button does not fill in a sample conclusion.</p><ul class='plain'>"
        + "".join(buttons)
        + "</ul>"
        + script
    )


def _sensory_body(payload: dict) -> str:
    if payload.get("ok") is False:
        return f"<p class='error'>{_esc(payload.get('code'))}: {_esc(payload.get('message'))}</p>"
    features = []
    for item in payload.get("browser_features") or []:
        features.append(
            f"<li>{_esc(item.get('id'))} {_pill(item.get('source_state'))} hardware {_pill(item.get('hardware_test'))}</li>"
        )
    hardware = payload.get("physical_hardware") or {}
    capture = payload.get("plugin_capture") or {}
    return (
        f"<p>Proof scope <code>{_esc(payload.get('proof_scope'))}</code></p>"
        f"<p>Physical hardware {_pill(hardware.get('state'))} receipt {_esc(hardware.get('receipt_value'))}</p>"
        f"<ul>{''.join(features)}</ul>"
        f"<p>Plugin camera {_esc(capture.get('camera'))}; microphone {_esc(capture.get('microphone'))}; biometric {_esc(capture.get('biometric'))}.</p>"
    )


def _integration_body(status: dict) -> str:
    return (
        "<ul>"
        "<li>Public MCP tools: no authorization header.</li>"
        "<li>Owner connection: UNAVAILABLE · OWNER_CONNECTION_DISABLED.</li>"
        "<li>State-changing owner actions: disabled.</li>"
        "<li>Sensor collection: not started by this Site.</li>"
        f"<li>Private bridge orbit {_pill((status.get('private_bridge_unauthenticated') or {}).get('orbit', {}).get('state'))}</li>"
        "</ul>"
        "<p>Composer mentions are specified for desktop ChatGPT. The global sidebar entry is specified for web and desktop. "
        "Mobile clients keep the same text tools when an interactive extension is absent.</p>"
    )


def _ci_body() -> str:
    options = "".join(f"<option value='{html.escape(name)}'>{html.escape(name)}</option>" for name in WORKFLOWS)
    return """
<p>A successful run is recorded at its head SHA. It is not promoted to live inference.</p>
<form id="ci-form">
  <label>Workflow <select name="workflow">OPTIONS</select></label>
  <button type="submit">Load runs</button>
</form>
<div id="ci-out"></div>
<script>
document.getElementById("ci-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const workflow = event.target.workflow.value;
  const slot = document.getElementById("ci-out");
  slot.textContent = "Retrieving GitHub runs…";
  const response = await fetch("/api/call", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: "beastbox_get_ci", arguments: {workflow: workflow, limit: 3}})
  });
  const payload = await response.json();
  slot.textContent = "";
  const note = document.createElement("p");
  note.textContent = "proves_live_inference=" + String(payload.proves_live_inference);
  slot.appendChild(note);
  (payload.runs || []).forEach((run) => {
    const row = document.createElement("p");
    row.textContent = String(run.record_state) + " conclusion=" + String(run.conclusion)
      + " " + String(run.head_sha) + " " + String(run.html_url || "");
    slot.appendChild(row);
  });
  if (payload.code) {
    const err = document.createElement("p");
    err.textContent = payload.code + " " + (payload.message || "");
    slot.appendChild(err);
  }
});
</script>
""".replace("OPTIONS", options)


def _fact(label: str, section: dict) -> str:
    detail = section.get("message") or section.get("scope") or section.get("subject") or ""
    code = section.get("code")
    extra = f" · {html.escape(str(code))}" if code else ""
    return f"<p><strong>{html.escape(label)}</strong> {_pill(section.get('state'))}{extra}<span class='detail'>{html.escape(str(detail))}</span></p>"


def _pill(state: object) -> str:
    text = state if isinstance(state, str) else "NOT YET VERIFIED"
    kind = PILL_CLASS.get(text, "unverified")
    return f"<span class='pill {kind}'>{html.escape(text)}</span>"


def _esc(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return html.escape(json.dumps(value, ensure_ascii=False))
    return html.escape(str(value))


def _section(anchor: str, title: str, body: str) -> str:
    return f"<section id='{anchor}'><h2>{html.escape(title)}</h2>{body}</section>"


def _page_open(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: dark; --bg:#070711; --panel:#10101c; --line:#2a3348; --text:#e8eaf4; --muted:#9aa3b8; --cyan:#3ee0ff; --violet:#c4b5fd; --amber:#f0c36a; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:radial-gradient(1200px 500px at 10% -10%, rgba(62,224,255,.16), transparent 50%), radial-gradient(900px 400px at 100% 0, rgba(167,139,250,.18), transparent 45%), var(--bg); color:var(--text); font:16px/1.5 ui-sans-serif, "Segoe UI", sans-serif; }}
  header, main, footer, nav {{ width:min(1080px, calc(100% - 28px)); margin:0 auto; }}
  header {{ padding:28px 0 8px; }}
  h1 {{ margin:0; font-size:clamp(1.6rem, 4vw, 2.4rem); letter-spacing:.03em; }}
  h2 {{ margin:0 0 10px; font-size:1.05rem; color:var(--cyan); }}
  h3 {{ margin:0 0 6px; font-size:.95rem; }}
  .kicker {{ margin:0 0 6px; color:var(--violet); letter-spacing:.14em; text-transform:uppercase; font-size:.75rem; }}
  .lede, .meta, .detail {{ color:var(--muted); }}
  .detail {{ display:block; }}
  .invariants {{ display:flex; flex-wrap:wrap; gap:8px; padding:0; list-style:none; }}
  .invariants li {{ border:1px solid var(--line); border-radius:999px; padding:4px 10px; }}
  nav {{ display:flex; flex-wrap:wrap; gap:8px 12px; padding:8px 0 18px; }}
  nav a {{ color:var(--cyan); text-decoration:none; }}
  section, .card {{ background:rgba(16,16,28,.92); border:1px solid var(--line); border-radius:16px; padding:16px; margin:0 0 14px; }}
  .modules {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:10px; }}
  .module {{ border:1px solid var(--line); border-radius:12px; padding:10px; }}
  .pill {{ display:inline-block; margin:0 4px; padding:1px 8px; border-radius:999px; border:1px solid var(--line); font-size:.72rem; letter-spacing:.04em; vertical-align:middle; }}
  .live {{ color:var(--cyan); }} .historical {{ color:var(--violet); }} .implemented {{ color:var(--text); }} .unavailable {{ color:var(--muted); }} .unverified {{ color:var(--amber); }}
  code, pre {{ font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  pre {{ white-space:pre-wrap; word-break:break-word; background:#09090f; padding:10px; border-radius:10px; max-height:320px; overflow:auto; }}
  button, select {{ background:#161626; color:var(--text); border:1px solid var(--line); border-radius:10px; padding:8px 10px; }}
  button {{ cursor:pointer; }}
  ul.plain {{ list-style:none; padding:0; }}
  footer {{ color:var(--muted); padding:8px 0 28px; }}
  .install {{ padding-top:24px; }}
  @media (max-width: 720px) {{
    body {{ font-size:15px; }}
    header, main, footer, nav {{ width:min(100% - 20px, 1080px); }}
    .invariants {{ display:grid; }}
    nav a {{ padding:6px 0; }}
  }}
</style>
</head>
<body>
"""
