"""Public evidence tools. Values come from live reads or are marked unavailable."""

from __future__ import annotations

import re
from typing import Any

from . import CONNECTOR, __version__
from .fetch import (
    FRONTEND_URL,
    RELEASE_URL,
    SourceBook,
    SourceError,
    bridge_url,
    commit_url,
    raw_url,
    workflow_runs_url,
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
INVARIANTS = ("MODEL ≠ MEMORY", "MODEL ≠ STATE", "MODEL ≠ AUTHORITY")

RESEARCH = {
    "self-correction-005": "docs/experiments/COSMOS_SELF_CORRECTION_005_RESULTS.md",
    "dyn12-controlled-006": "docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md",
    "learning-challenge-001": "docs/experiments/COSMOS_LEARNING_CHALLENGE_001_RESULTS.md",
    "native-correction-002": "docs/experiments/COSMOS_NATIVE_CORRECTION_002_RESULTS.md",
    "micro-originals-004": "docs/experiments/COSMOS_MICRO_ORIGINALS_004_RESULTS.md",
    "small-model-controls-003": "docs/experiments/COSMOS_SMALL_MODEL_CONTROLS_003_RESULTS.md",
    "substrate-activation-007": "docs/experiments/COSMOS_SUBSTRATE_ACTIVATION_007_RESULTS.md",
    "persistent-substrate-swap-002": "docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md",
    "zero-api-original-native-003": "docs/experiments/BEASTBOX_ZERO_API_ORIGINAL_NATIVE_003_RESULTS.md",
}

WORKFLOWS = {
    "ci": "ci.yml",
    "product-ci": "product-ci.yml",
    "rust": "rust.yml",
    "cypher-smoke": "cypher-smoke.yml",
    "public-production-smoke": "unified-public-production-smoke.yml",
}

MANIFEST_PATH = "docs/ECOSYSTEM_MANIFEST.json"
PROVIDERS_PATH = "beastbox/providers.py"
EXCERPT_HINTS = ("conclusion", "interpretation", "claim boundary", "final answer", "result")

PROVIDER_NOTES = {
    "ReferenceTextProvider": (
        "fixture",
        "Deterministic reference text fixture present in source. It is not a trained model "
        "and this connector does not treat it as live production inference.",
    ),
    "LocalOllamaProvider": (
        "adapter",
        "Source-supported local Ollama adapter. Public production has not verified that this adapter is installed or serving.",
    ),
    "CompatibleChatProvider": (
        "adapter",
        "Source-supported OpenAI-compatible chat adapter. Public production has not verified a live deployment of it.",
    ),
}
SKIP_CLASSES = {"TextProvider", "ProviderDiagnosticError"}

OWNER_TOOLS = {
    "beastbox_owner_inspect_memory": {
        "title": "Inspect owner memory summaries",
        "state_changing": False,
        "backend_routes": ["GET /api/memory", "GET /api/orbit"],
        "backend_supports": True,
    },
    "beastbox_owner_inspect_runtime": {
        "title": "Inspect owner runtime traces and provider identity",
        "state_changing": False,
        "backend_routes": ["GET /api/trace", "GET /api/provider"],
        "backend_supports": True,
    },
    "beastbox_owner_request_inference": {
        "title": "Request owner inference",
        "state_changing": True,
        "backend_routes": ["POST /api/chat", "POST /api/chat-start"],
        "backend_supports": True,
    },
    "beastbox_owner_read_observations": {
        "title": "Read authorized sensor-derived observations",
        "state_changing": False,
        "backend_routes": ["GET /api/observations"],
        "backend_supports": True,
    },
    "beastbox_owner_request_activation": {
        "title": "Request a bounded activation task",
        "state_changing": True,
        "backend_routes": ["POST /api/activation"],
        "backend_supports": True,
    },
    "beastbox_owner_request_model_change": {
        "title": "Request an owner-approved model change",
        "state_changing": True,
        "backend_routes": ["POST /api/models"],
        "backend_supports": True,
    },
    "beastbox_owner_emergency_stop": {
        "title": "Activate the owner emergency stop",
        "state_changing": True,
        "backend_routes": ["POST /api/authority {action: master_stop}"],
        "backend_supports": True,
    },
}

FORBIDDEN_ARGUMENT_KEYS = {
    "token",
    "authorization",
    "bearer",
    "secret",
    "password",
    "api_key",
    "apikey",
    "credential",
    "railway_token",
}

CLAIM_KEYS = {"claim_live_inference", "claim_physical_capture", "claim_ci_proves_inference"}


def envelope(tool: str, book: SourceBook, sources: list[dict], **fields: Any) -> dict:
    return {
        "ok": True,
        "tool": tool,
        "timestamp": book.now(),
        "provenance": {
            "connector": CONNECTOR,
            "version": __version__,
            "sources": sources,
        },
        "invariants": list(INVARIANTS),
        **fields,
    }


def failure(
    tool: str, book: SourceBook, code: str, message: str, sources: list[dict] | None = None, **fields: Any
) -> dict:
    body = envelope(tool, book, sources or [], code=code, message=message, **fields)
    body["ok"] = False
    return body


def _claims(arguments: dict) -> dict | None:
    flagged = [key for key in CLAIM_KEYS if arguments.get(key) is True]
    if not flagged:
        return None
    return {
        "code": "FALSE_STATUS_CLAIM",
        "message": "Refusing a request to mark inference or physical capture as verified.",
        "rejected_fields": flagged,
        "live_inference": {
            "state": "NOT YET VERIFIED",
            "connector_invoked_model": False,
            "proved_by_github_check": False,
            "proved_by_bridge_health": False,
            "proved_by_release_receipt": False,
        },
        "physical_sensor_capture": {
            "state": "NOT YET VERIFIED",
            "connector_started_capture": False,
        },
    }


def _reject_secrets(arguments: dict) -> str | None:
    for key in arguments:
        if key.lower() in FORBIDDEN_ARGUMENT_KEYS:
            return "credentials are not accepted by this connector"
    for value in arguments.values():
        if isinstance(value, str) and "bearer " in value.lower():
            return "credentials are not accepted by this connector"
    return None


def _bool_field(arguments: dict, key: str) -> str | None:
    if key in arguments and type(arguments[key]) is not bool:
        return f"{key} must be a boolean"
    return None


def validate(tool: str, arguments: object) -> str | None:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return "arguments must be an object"
    secret = _reject_secrets(arguments)
    if secret:
        return secret
    allowed = _allowed_keys(tool)
    extra = sorted(set(arguments) - allowed)
    if extra:
        return "unsupported arguments: " + ", ".join(extra)
    for key in CLAIM_KEYS:
        problem = _bool_field(arguments, key)
        if problem:
            return problem
    if tool == "beastbox_get_architecture" and "component" in arguments:
        component = arguments["component"]
        if not isinstance(component, str) or not re.fullmatch(r"[a-z0-9-]{1,64}", component):
            return "component must be a lowercase id"
    if tool == "beastbox_list_models":
        problem = _bool_field(arguments, "include_historical")
        if problem:
            return problem
    if tool == "beastbox_get_research":
        experiment = arguments.get("experiment")
        if not isinstance(experiment, str) or experiment not in RESEARCH:
            return "experiment must be one of the published ids"
    if tool == "beastbox_get_ci":
        workflow = arguments.get("workflow")
        if not isinstance(workflow, str) or workflow not in WORKFLOWS:
            return "workflow must be one of the known workflow ids"
        if "limit" in arguments:
            limit = arguments["limit"]
            if type(limit) is not int or not 1 <= limit <= 5:
                return "limit must be an integer from 1 to 5"
    if tool == "beastbox_search_mentions":
        query = arguments.get("query")
        if not isinstance(query, str) or len(query) > 80:
            return "query must be a string of at most 80 characters"
        if any(ord(char) < 32 for char in query):
            return "query contains unsupported control characters"
    return None


def _allowed_keys(tool: str) -> set[str]:
    common = set(CLAIM_KEYS)
    specific = {
        "beastbox_get_status": set(),
        "beastbox_get_architecture": {"component"},
        "beastbox_list_models": {"include_historical"},
        "beastbox_get_research": {"experiment"},
        "beastbox_get_sensory_status": set(),
        "beastbox_get_ci": {"workflow", "limit"},
        "beastbox_search_mentions": {"query"},
        "beastbox_open_dashboard": set(),
    }
    if tool in OWNER_TOOLS:
        return common
    return common | specific.get(tool, set())


def call_tool(name: str, arguments: object, book: SourceBook) -> tuple[dict, bool]:
    if not isinstance(arguments, dict) and arguments is not None:
        return failure(name, book, "INVALID_INPUT", "arguments must be an object"), True
    arguments = arguments or {}
    problem = validate(name, arguments)
    if problem:
        code = "INVALID_INPUT"
        if _reject_secrets(arguments):
            code = "INVALID_INPUT"
        return failure(name, book, code, problem), True
    claim = _claims(arguments)
    if claim:
        return failure(
            name,
            book,
            claim["code"],
            claim["message"],
            rejected_fields=claim["rejected_fields"],
            live_inference=claim["live_inference"],
            physical_sensor_capture=claim["physical_sensor_capture"],
        ), True
    if name in OWNER_TOOLS:
        return _owner_disabled(name, book), True
    handler = {
        "beastbox_get_status": tool_status,
        "beastbox_get_architecture": tool_architecture,
        "beastbox_list_models": tool_models,
        "beastbox_get_research": tool_research,
        "beastbox_get_sensory_status": tool_sensory,
        "beastbox_get_ci": tool_ci,
        "beastbox_search_mentions": tool_mentions,
        "beastbox_open_dashboard": tool_dashboard,
    }.get(name)
    if handler is None:
        return failure(name, book, "NOT_FOUND", "unknown tool"), True
    try:
        payload = handler(arguments, book)
    except SourceError as exc:
        return failure(name, book, exc.code, exc.message, [exc.source] if exc.source else []), True
    return payload, not payload.get("ok", False)


def tool_status(arguments: dict, book: SourceBook) -> dict:
    sources: list[dict] = []
    release_section = _section_from(lambda: _release_section(book), sources)
    github_section = _section_from(lambda: _github_main(book), sources)
    frontend_section = _section_from(lambda: _frontend(book), sources)
    readiness_section = _section_from(lambda: _readiness(book), sources)
    orbit = _section_from(lambda: _unauthenticated(book, "/api/orbit"), sources)
    models = _section_from(lambda: _unauthenticated(book, "/api/models"), sources)
    release_body = release_section.get("receipt") if release_section.get("state") == "VERIFIED LIVE" else None
    activation_value = None if not isinstance(release_body, dict) else release_body.get("backend_activation_verified")
    hardware_value = None if not isinstance(release_body, dict) else release_body.get("physical_hardware_verified")
    sha = github_section.get("sha")
    marker = release_section.get("source_marker")
    prefix = marker.rsplit("-", 1)[-1] if isinstance(marker, str) else ""
    marker_matches = bool(sha and prefix and sha.startswith(prefix) and len(prefix) >= 7)
    return envelope(
        "beastbox_get_status",
        book,
        sources,
        live_inference={
            "state": "NOT YET VERIFIED",
            "connector_invoked_model": False,
            "proved_by_github_check": False,
            "proved_by_bridge_health": False,
            "proved_by_release_receipt": False,
        },
        physical_sensor_capture={
            "state": _hardware_state(release_body),
            "receipt_value": hardware_value,
            "proof_scope": None if not isinstance(release_body, dict) else release_body.get("proof_scope"),
            "connector_started_capture": False,
        },
        release=release_section,
        github_main=github_section,
        deployment_identity={
            "state": "NOT YET VERIFIED",
            "release_marker": marker,
            "github_main_sha": sha,
            "marker_matches_main_prefix": marker_matches,
            "scope": "The public release marker and GitHub main are separate observations. A prefix match is not a deployment attestation.",
        },
        frontend=frontend_section,
        backend_readiness=readiness_section,
        backend_activation={
            "state": _receipt_bool_state(activation_value),
            "receipt_value": activation_value,
            "scope": "Public release field backend_activation_verified. This connector did not call a model.",
        },
        private_bridge_unauthenticated={
            "orbit": orbit,
            "models": models,
            "scope": "Unauthenticated GET only. No owner credential was sent.",
        },
    )


def tool_architecture(arguments: dict, book: SourceBook) -> dict:
    sha, commit_source = _require_sha(book)
    payload, source = book.get_json(raw_url(sha, MANIFEST_PATH))
    if not isinstance(payload, dict) or not isinstance(payload.get("components"), list):
        raise SourceError("UPSTREAM_UNAVAILABLE", "ecosystem manifest shape was not recognized", source)
    wanted = arguments.get("component")
    components = []
    for item in payload["components"]:
        if not isinstance(item, dict):
            continue
        if wanted and item.get("id") != wanted:
            continue
        repository_status = item.get("status")
        components.append(
            {
                "id": item.get("id"),
                "names": item.get("names"),
                "repository_status": repository_status,
                "connect_state": _manifest_state(repository_status),
                "boundary": item.get("boundary"),
                "paths": item.get("paths"),
                "origin": item.get("origin"),
            }
        )
    if wanted and not components:
        return failure(
            "beastbox_get_architecture",
            book,
            "NOT_FOUND",
            "component id is not in the ecosystem manifest",
            [commit_source, source],
        )
    return envelope(
        "beastbox_get_architecture",
        book,
        [commit_source, source],
        retrieval_state="VERIFIED LIVE",
        source_revision=sha,
        manifest_schema=payload.get("schema"),
        manifest_generated_from_commit=payload.get("generated_from_commit"),
        manifest_status_rule=payload.get("status_rule"),
        evidence_url=raw_url(sha, MANIFEST_PATH),
        scope="Repository manifest at the resolved main SHA. This is not a live process map.",
        components=components,
    )


def tool_models(arguments: dict, book: SourceBook) -> dict:
    sha, commit_source = _require_sha(book)
    text, truncated, source = book.get_text(raw_url(sha, PROVIDERS_PATH), limit=80_000)
    release, release_source = _release_soft(book)
    activation = None if release is None else release.get("backend_activation_verified")
    classes = re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\b", text, flags=re.MULTILINE)
    identities = []
    for name in classes:
        if name.startswith("_") or name in SKIP_CLASSES:
            continue
        kind, detail = PROVIDER_NOTES.get(
            name, ("artifact", "Class present in beastbox/providers.py. No live production role is inferred.")
        )
        identities.append(
            {
                "name": name,
                "kind": kind,
                "source_state": "IMPLEMENTED",
                "installed_in_public_production": "NOT YET VERIFIED",
                "historical_test": False,
                "live_production": "NOT YET VERIFIED",
                "detail": detail,
            }
        )
    historical = None
    sources = [commit_source, source]
    if release_source:
        sources.append(release_source)
    if arguments.get("include_historical") is True:
        try:
            historical, historical_source = _historical_models(book, sha)
            sources.append(historical_source)
        except SourceError as exc:
            historical = {"state": "UNAVAILABLE", "code": exc.code, "message": exc.message}
            if exc.source:
                sources.append(exc.source)
    return envelope(
        "beastbox_list_models",
        book,
        sources,
        retrieval_state="VERIFIED LIVE",
        source_revision=sha,
        providers_path=PROVIDERS_PATH,
        providers_truncated=truncated,
        evidence_url=raw_url(sha, PROVIDERS_PATH),
        identities=identities,
        historical=historical,
        live_production_verification={
            "state": "NOT YET VERIFIED",
            "receipt_backend_activation_verified": activation,
            "receipt_field_state": _receipt_bool_state(activation),
            "reason": "Provider classes and historical reports are not live production verification.",
        },
        scope="Source inventory. A class or a past experiment is not a running production model.",
    )


def tool_research(arguments: dict, book: SourceBook) -> dict:
    experiment = arguments["experiment"]
    path = RESEARCH[experiment]
    sha, commit_source = _require_sha(book)
    text, truncated, source = book.get_text(raw_url(sha, path), limit=20_000)
    heading, excerpt, excerpt_truncated = _excerpt(text)
    return envelope(
        "beastbox_get_research",
        book,
        [commit_source, source],
        experiment=experiment,
        path=path,
        source_revision=sha,
        retrieval_state="VERIFIED LIVE",
        state="VERIFIED HISTORICAL",
        evidence_url=raw_url(sha, path),
        github_blob_url=f"https://github.com/{'NavisWORLD/The-beast-box-'}/blob/{sha}/{path}",
        title=_title(text),
        excerpt_heading=heading,
        original_text=excerpt,
        truncated=truncated or excerpt_truncated,
        connector_conclusion=None,
        scope="Published repository text at the resolved main SHA. This connector does not rewrite the result.",
    )


def tool_sensory(arguments: dict, book: SourceBook) -> dict:
    release, source = _release(book)
    features = release.get("browser_features")
    feature_rows = []
    if isinstance(features, list):
        for item in features:
            if isinstance(item, str):
                feature_rows.append(
                    {
                        "id": item,
                        "source_state": "IMPLEMENTED",
                        "hardware_test": "NOT YET VERIFIED",
                        "scope": "Named by the public release receipt as deployed code, not as a physical sensor test.",
                    }
                )
    hardware = release.get("physical_hardware_verified")
    return envelope(
        "beastbox_get_sensory_status",
        book,
        [source],
        proof_scope=release.get("proof_scope"),
        physical_hardware={
            "state": _hardware_state(release),
            "receipt_value": hardware,
            "scope": "physical_hardware_verified on the public release receipt. A true flag still requires proof_scope physical_sensor_test before this connector marks it VERIFIED LIVE.",
        },
        browser_features=feature_rows,
        plugin_capture={
            "camera": "not activated",
            "microphone": "not activated",
            "biometric": "not activated",
            "state": "IMPLEMENTED",
            "scope": "This connector has no capture path.",
        },
        live_sensor_capture={
            "state": "NOT YET VERIFIED",
            "connector_started_capture": False,
        },
    )


def tool_ci(arguments: dict, book: SourceBook) -> dict:
    workflow = arguments["workflow"]
    limit = arguments.get("limit", 3)
    filename = WORKFLOWS[workflow]
    payload, source = book.get_json(workflow_runs_url(filename, limit))
    runs_in = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs_in, list):
        raise SourceError("UPSTREAM_UNAVAILABLE", "workflow runs payload was not recognized", source)
    runs = []
    for item in runs_in[:limit]:
        if not isinstance(item, dict):
            continue
        conclusion = item.get("conclusion")
        status = item.get("status")
        if status != "completed":
            record_state = "NOT YET VERIFIED"
        else:
            record_state = "VERIFIED HISTORICAL"
        runs.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "head_sha": item.get("head_sha"),
                "conclusion": conclusion,
                "status": status,
                "html_url": item.get("html_url"),
                "created_at": item.get("created_at"),
                "event": item.get("event"),
                "record_state": record_state,
                "proves_live_inference": False,
                "proves_physical_sensor_capture": False,
                "scope": "GitHub Actions record for this head_sha. Success is source verification, not live inference or sensor capture.",
            }
        )
    return envelope(
        "beastbox_get_ci",
        book,
        [source],
        workflow=workflow,
        workflow_file=filename,
        retrieval_state="VERIFIED LIVE",
        proves_live_inference=False,
        proves_physical_sensor_capture=False,
        runs=runs,
        scope="Recent workflow runs. A green check does not prove a live model or a physical sensor.",
    )


def tool_mentions(arguments: dict, book: SourceBook) -> dict:
    query = arguments.get("query", "")
    folded = query.casefold().strip()
    items = []
    for item in _mention_catalog():
        haystack = " ".join([item["name"], item.get("description", ""), item["uri"]]).casefold()
        if folded and folded not in haystack:
            continue
        items.append(
            {
                "type": "resource_link",
                "uri": item["uri"],
                "name": item["name"],
                "description": item["description"],
            }
        )
        if len(items) == 12:
            break
    return envelope(
        "beastbox_search_mentions",
        book,
        [],
        items=items,
        query=query,
        platform_note="Composer at-mentions are a desktop ChatGPT extension. Web and mobile clients may not show this picker. The same evidence remains available through the read-only tools.",
    )


def tool_dashboard(arguments: dict, book: SourceBook) -> dict:
    status, status_error = call_tool("beastbox_get_status", {}, book)
    architecture, architecture_error = call_tool("beastbox_get_architecture", {}, book)
    sensory, sensory_error = call_tool("beastbox_get_sensory_status", {}, book)
    sources: list[dict] = []
    for part in (status, architecture, sensory):
        sources.extend(part.get("provenance", {}).get("sources", []))
    components = architecture.get("components") if not architecture_error else []
    summary = []
    if isinstance(components, list):
        for item in components:
            if isinstance(item, dict):
                summary.append(
                    {
                        "id": item.get("id"),
                        "connect_state": item.get("connect_state"),
                        "repository_status": item.get("repository_status"),
                        "boundary": item.get("boundary"),
                    }
                )
    return envelope(
        "beastbox_open_dashboard",
        book,
        sources,
        status=status,
        architecture_summary=summary,
        architecture_error=architecture.get("code") if architecture_error else None,
        sensory=sensory,
        sensory_error=sensory.get("code") if sensory_error else None,
        research_catalog=[{"experiment": key, "path": path, "state": "IMPLEMENTED"} for key, path in RESEARCH.items()],
        owner_connection=_owner_gate(),
        runtime_versus_history={
            "runtime_status": "backend readiness and the public website are runtime observations",
            "historical_results": "research receipts and GitHub conclusions stay historical",
            "github_success_proves_live_inference": False,
        },
    )


def _owner_disabled(name: str, book: SourceBook) -> dict:
    spec = OWNER_TOOLS[name]
    return failure(
        name,
        book,
        "OWNER_CONNECTION_DISABLED",
        "Owner connection is disabled. No bridge credential is configured, and no owner route was called.",
        bridge_called=False,
        credential_present=False,
        state_changed=False,
        sensor_capture_started=False,
        self_grant=False,
        backend_supports=spec["backend_supports"],
        state_changing=spec["state_changing"],
        backend_routes=spec["backend_routes"],
        authorization_requirements=_authorization_requirements(spec["state_changing"]),
    )


def _authorization_requirements(state_changing: bool) -> list[str]:
    requirements = [
        "Configure a server-side owner credential as a Sites secret. Do not commit it or copy the Railway bearer token into the Site.",
        "The credential must be scoped to the listed existing bridge route and checked on the server for every call.",
        "A browser login cookie or Sign in with ChatGPT header is not authorization for the owner bridge.",
        "This connector must not gain a tool that grants itself a broader scope.",
        "Sensor routes stay explicitly approved. The connector must not start a camera, microphone, or biometric capture.",
    ]
    if state_changing:
        requirements.append(
            "State-changing tools stay off until production backup, isolated restoration, deployment, and live acceptance are independently recorded."
        )
    return requirements


def _owner_gate() -> dict:
    return {
        "state": "UNAVAILABLE",
        "code": "OWNER_CONNECTION_DISABLED",
        "credential_present": False,
        "bridge_called": False,
        "state_changing_enabled": False,
        "tools": list(OWNER_TOOLS),
    }


def _mention_catalog() -> list[dict]:
    items = [
        {
            "uri": "cosmos://evidence/status",
            "name": "Deployment status",
            "description": "Public release, GitHub main, frontend and backend readiness",
        },
        {
            "uri": "cosmos://evidence/architecture",
            "name": "COSMOS architecture",
            "description": "Repository ecosystem manifest and module boundaries",
        },
        {
            "uri": "cosmos://evidence/models",
            "name": "Model inventory",
            "description": "Source provider classes, historical reports, live verification gap",
        },
        {
            "uri": "cosmos://evidence/senses",
            "name": "Sensory status",
            "description": "Implemented browser features and hardware-test limits",
        },
        {
            "uri": "cosmos://evidence/ci",
            "name": "GitHub verification",
            "description": "Recent workflow runs and their exact revisions",
        },
        {
            "uri": "cosmos://invariant/model-memory",
            "name": "MODEL ≠ MEMORY",
            "description": "A model is not the durable substrate",
        },
        {
            "uri": "cosmos://invariant/model-state",
            "name": "MODEL ≠ STATE",
            "description": "A model is not the retained state",
        },
        {
            "uri": "cosmos://invariant/model-authority",
            "name": "MODEL ≠ AUTHORITY",
            "description": "A model does not hold authority",
        },
    ]
    for experiment, path in RESEARCH.items():
        items.append(
            {
                "uri": f"cosmos://evidence/research/{experiment}",
                "name": experiment,
                "description": path,
            }
        )
    return items


def _section_from(loader, sources: list[dict]) -> dict:
    try:
        section = loader()
    except SourceError as exc:
        if exc.source:
            sources.append(exc.source)
        return {
            "state": "UNAVAILABLE",
            "code": exc.code,
            "message": exc.message,
        }
    source = section.pop("_source", None)
    if source:
        sources.append(source)
    return section


def _hardware_state(release: object) -> str:
    if not isinstance(release, dict) or "physical_hardware_verified" not in release:
        return "UNAVAILABLE"
    if release.get("physical_hardware_verified") is True and release.get("proof_scope") == "physical_sensor_test":
        return "VERIFIED LIVE"
    return "NOT YET VERIFIED"


def _release_section(book: SourceBook) -> dict:
    payload, source = _release(book)
    return {
        "_source": source,
        "state": "VERIFIED LIVE",
        "http_status": source.get("http_status"),
        "schema": payload.get("schema"),
        "source_marker": payload.get("source_marker"),
        "proof_scope": payload.get("proof_scope"),
        "backend_activation_verified": payload.get("backend_activation_verified"),
        "physical_hardware_verified": payload.get("physical_hardware_verified"),
        "browser_features": payload.get("browser_features"),
        "receipt": payload,
        "url": RELEASE_URL,
    }


def _release(book: SourceBook) -> tuple[dict, dict]:
    payload, source = book.get_json(RELEASE_URL)
    if not isinstance(payload, dict):
        raise SourceError("UPSTREAM_UNAVAILABLE", "release receipt was not a JSON object", source)
    return payload, source


def _release_soft(book: SourceBook) -> tuple[dict | None, dict | None]:
    try:
        return _release(book)
    except SourceError:
        return None, None


def _require_sha(book: SourceBook) -> tuple[str, dict]:
    section = _github_main(book)
    sha = section.get("sha")
    source = section["_source"]
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise SourceError("UPSTREAM_UNAVAILABLE", "GitHub main did not return a commit SHA", source)
    return sha, source


def _github_main(book: SourceBook) -> dict:
    payload, source = book.get_json(commit_url())
    if not isinstance(payload, dict):
        raise SourceError("UPSTREAM_UNAVAILABLE", "GitHub commit payload was not an object", source)
    sha = payload.get("sha")
    commit = payload.get("commit") if isinstance(payload.get("commit"), dict) else {}
    message = commit.get("message") if isinstance(commit.get("message"), str) else ""
    committer = commit.get("committer") if isinstance(commit.get("committer"), dict) else {}
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise SourceError("UPSTREAM_UNAVAILABLE", "GitHub main did not return a commit SHA", source)
    return {
        "_source": source,
        "state": "VERIFIED LIVE",
        "sha": sha,
        "html_url": payload.get("html_url"),
        "committed_at": committer.get("date"),
        "subject": message.splitlines()[0][:200] if message else None,
        "proves_live_inference": False,
        "proves_physical_sensor_capture": False,
        "scope": "GitHub main revision lookup. This is not proof of live inference or of the deployed website SHA.",
    }


def _frontend(book: SourceBook) -> dict:
    text, _truncated, source = book.get_text(FRONTEND_URL, limit=20_000)
    found = "cosmos" in text.casefold() or "beast" in text.casefold()
    return {
        "_source": source,
        "state": "VERIFIED LIVE",
        "http_status": source.get("http_status"),
        "final_url": source.get("url"),
        "content_marker": "VERIFIED LIVE" if found else "NOT YET VERIFIED",
        "scope": "Public website HTTP response only. Not backend activation.",
    }


def _readiness(book: SourceBook) -> dict:
    payload, source = book.get_json(bridge_url("/healthz"))
    ready = isinstance(payload, dict) and payload.get("ready") is True
    service = payload.get("service") if isinstance(payload, dict) else None
    return {
        "_source": source,
        "state": "VERIFIED LIVE" if ready else "NOT YET VERIFIED",
        "http_status": source.get("http_status"),
        "ready": payload.get("ready") if isinstance(payload, dict) else None,
        "service": service,
        "inference_state": "NOT YET VERIFIED",
        "proves_live_inference": False,
        "scope": "Railway /healthz process readiness only. Not inference, memory, or owner data.",
    }


def _unauthenticated(book: SourceBook, path: str) -> dict:
    result, source = book.get_response(bridge_url(path))
    snippet = None
    if result.status == 401:
        text = result.body.decode("utf-8", errors="replace")[:180]
        if "bearer" not in text.lower() and "token" not in text.lower():
            snippet = text
    state = "VERIFIED LIVE" if result.status == 401 else "NOT YET VERIFIED"
    section = {
        "_source": source,
        "state": state,
        "http_status": result.status,
        "scope": "Observed without a credential. A 401 is the expected rejection.",
    }
    if snippet is not None:
        section["body_snippet"] = snippet
    if result.status == 200:
        section["body_withheld"] = True
        section["message"] = "Unexpected unauthenticated success. Body withheld."
    return section


def _historical_models(book: SourceBook, sha: str) -> tuple[dict, dict]:
    path = RESEARCH["persistent-substrate-swap-002"]
    text, truncated, source = book.get_text(raw_url(sha, path), limit=12_000)
    heading, excerpt, excerpt_truncated = _excerpt(text)
    return {
        "state": "VERIFIED HISTORICAL",
        "path": path,
        "source_revision": sha,
        "evidence_url": raw_url(sha, path),
        "excerpt_heading": heading,
        "original_text": excerpt,
        "truncated": truncated or excerpt_truncated,
        "live_production": "NOT YET VERIFIED",
        "scope": "Published swap report text. These identities are not a live production inventory.",
    }, source


def _receipt_bool_state(value: object) -> str:
    if value is True:
        return "VERIFIED LIVE"
    if value is False:
        return "NOT YET VERIFIED"
    return "UNAVAILABLE"


def _manifest_state(status: object) -> str:
    if status in {"PRODUCT", "EXPERIMENTAL", "OPTIONAL INTEGRATION"}:
        return "IMPLEMENTED"
    if status in {"VERIFIED RESULT", "HISTORICAL EVIDENCE"}:
        return "VERIFIED HISTORICAL"
    if status == "NOT IMPLEMENTED":
        return "UNAVAILABLE"
    return "NOT YET VERIFIED"


def _title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:200]
    return None


def _excerpt(text: str) -> tuple[str, str, bool]:
    lines = text.splitlines()
    start = 0
    heading = "document opening"
    for index, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip().lower()
        if any(hint in stripped for hint in EXCERPT_HINTS) and line.strip().startswith("#"):
            start = index
            heading = line.strip().lstrip("#").strip()[:160]
            break
    excerpt = "\n".join(lines[start:]).strip()
    limit = 3500
    return heading, excerpt[:limit], len(excerpt) > limit
