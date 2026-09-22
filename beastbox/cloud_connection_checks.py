"""Explicit owner-initiated read-only connection checks. No inference or quantum jobs.

Never expose remote response bodies, tokens, URL queries or exception strings.
Only fixed HTTPS provider endpoints are used (no arbitrary user-supplied URLs).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
import urllib.error
import urllib.parse
import urllib.request
from .cloud_connections import ConnectionError

# A bounded Azure result vocabulary. Never return an SDK exception, service
# error body, request URL, credential fragment, or storage account identifier.
AZURE_DETAILS = {
    "SAS_FORMAT_INVALID": "Saved credential is not a standalone container SAS query token. Account keys, connection strings and full URLs cannot be used in this field.",
    "SAS_SCOPE_INVALID": "Saved SAS is not explicitly scoped to this container (sr=c). Generate a least-privilege container SAS.",
    "SAS_READ_PERMISSION_MISSING": "Saved container SAS lacks read (r) permission needed by the metadata check.",
    "SAS_EXPIRED": "Saved SAS is expired. Replace it through the private owner settings without changing other keys.",
    "SAS_NOT_YET_VALID": "Saved SAS start time is in the future. Check SAS start time and clock skew.",
    "SAS_TIME_INVALID": "Saved SAS time fields are invalid. Create a fresh container SAS with a valid UTC expiry.",
    "AZURE_CONTAINER_NOT_FOUND": "The account or private container could not be found, or its existence was concealed by access rules. Check the exact container in Azure.",
    "AZURE_AUTH_REJECTED": "Azure rejected the SAS. Verify its signature, account and signing-key rotation; do not paste the token into chat.",
    "AZURE_PERMISSION_DENIED": "Azure denied the container-properties read. Check SAS scope, permissions, network restrictions and storage firewall.",
    "AZURE_RATE_LIMITED": "Azure throttled the read-only container check. No retries were attempted.",
    "AZURE_TIMEOUT": "Azure did not complete the read-only check before its timeout. No retries were attempted.",
    "AZURE_NETWORK_UNAVAILABLE": "The host could not reach Azure Blob. Check Railway egress, Azure networking and private-endpoint restrictions.",
    "AZURE_REMOTE_UNAVAILABLE": "Azure returned an unclassified error. Container access has not been verified.",
}


def _azure_check_result(status: str) -> dict:
    return {"provider": "azure_blob", "status": status, "detail": AZURE_DETAILS[status]}


def _utc_sas_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("SAS timestamp must include UTC offset")
    return result.astimezone(timezone.utc)


def _azure_sas_preflight(secret: str, now: datetime | None = None) -> str | None:
    """Validate only SAS shape, scope, permission and validity window locally."""
    if not isinstance(secret, str) or secret.startswith(("https://", "http://")) or "AccountKey=" in secret or "SharedAccessSignature=" in secret:
        return "SAS_FORMAT_INVALID"
    try:
        query = urllib.parse.parse_qs(secret.lstrip("?"), strict_parsing=True, keep_blank_values=True)
    except (ValueError, UnicodeError):
        return "SAS_FORMAT_INVALID"
    def one(key: str) -> str | None:
        value = query.get(key)
        return value[0] if value and len(value) == 1 and value[0] else None
    if not one("sig") or not one("sv") or not one("sp") or not one("se"):
        return "SAS_FORMAT_INVALID"
    if one("sr") != "c":
        return "SAS_SCOPE_INVALID"
    if "r" not in one("sp"):
        return "SAS_READ_PERMISSION_MISSING"
    try:
        current = now or datetime.now(timezone.utc)
        if _utc_sas_time(one("se")) <= current:
            return "SAS_EXPIRED"
        start = one("st")
        if start and _utc_sas_time(start) > current + timedelta(minutes=5):
            return "SAS_NOT_YET_VALID"
    except (ValueError, TypeError, OverflowError):
        return "SAS_TIME_INVALID"
    return None

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ConnectionError("provider verification refused an HTTP redirect")


def verify_connection(provider: str, record: dict, opener=None) -> dict:
    """Read-only check; a valid token alone never proves inference or storage writes."""
    config,secret=record["config"],record["secret"]
    if provider=="ibm_quantum":
        return {"provider":provider,"status":"NOT_TESTED","detail":"IBM Quantum instance and job permissions require a separate authorized integration."}
    if provider=="azure_blob":
        mode = config.get("auth_mode", "container_sas")
        if mode == "container_sas":
            preflight = _azure_sas_preflight(secret)
            if preflight:
                return _azure_check_result(preflight)
        elif mode != "account_key":
            return _azure_check_result("SAS_FORMAT_INVALID")
        try:
            from azure.core.exceptions import HttpResponseError
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            return {"provider":provider,"status":"NOT_TESTED","detail":"Azure Blob SDK not installed on durable host."}
        try:
            base="https://"+config["account"]+".blob.core.windows.net"
            client=BlobServiceClient(account_url=base,credential=secret)
            client.get_container_client(config["container"]).get_container_properties(
                timeout=5,connection_timeout=5,read_timeout=5,retry_total=0)
            return {"provider":provider,"status":"CONTAINER_READ_VERIFIED",
                    "detail":"Container metadata read verified; object retrieval, writes, retention and chat integration NOT verified.",
                    "auth_mode": mode}
        except HttpResponseError as exc:
            # Do not reflect SDK message, response headers, request URI or SAS.
            status = exc.status_code
            code = {400:"AZURE_AUTH_REJECTED",401:"AZURE_AUTH_REJECTED",
                    403:"AZURE_PERMISSION_DENIED",404:"AZURE_CONTAINER_NOT_FOUND",
                    408:"AZURE_TIMEOUT",429:"AZURE_RATE_LIMITED",
                    500:"AZURE_REMOTE_UNAVAILABLE",502:"AZURE_REMOTE_UNAVAILABLE",
                    503:"AZURE_REMOTE_UNAVAILABLE",504:"AZURE_TIMEOUT"}.get(status,"AZURE_REMOTE_UNAVAILABLE")
            return _azure_check_result(code)
        except (TimeoutError,):
            return _azure_check_result("AZURE_TIMEOUT")
        except (OSError,):
            return _azure_check_result("AZURE_NETWORK_UNAVAILABLE")
        except Exception:
            return _azure_check_result("AZURE_REMOTE_UNAVAILABLE")
    if provider not in ("huggingface","ollama_cloud","ibm_watsonx"):
        raise ConnectionError("unsupported connection test provider")
    client=opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}),NoRedirect())
    if provider=="huggingface":
        target="https://huggingface.co/api/whoami-v2"
        headers={"Authorization":"Bearer "+secret,"Accept":"application/json"}
        req=urllib.request.Request(target,headers=headers,method="GET")
        valid_status="ACCOUNT_AUTH_VERIFIED"
        note="Account token accepted. Inference entitlement and model access NOT verified."
    elif provider=="ollama_cloud":
        target="https://ollama.com/v1/models"
        req=urllib.request.Request(target,headers={"Authorization":"Bearer "+secret,
            "Accept":"application/json"},method="GET")
        # Ollama's /v1/models list is public. A 200 cannot attest whether the
        # submitted API key is valid, has credit, or may generate with a model.
        valid_status="MODEL_LISTED_AUTH_UNVERIFIED"
        note="The public direct-API model list contains the saved ID. API key, account entitlement, generation, usage and costs have NOT been verified."
    else:
        req=urllib.request.Request("https://iam.cloud.ibm.com/identity/token",
            data=urllib.parse.urlencode({"grant_type":"urn:ibm:params:oauth:grant-type:apikey",
            "apikey":secret}).encode(),headers={"Content-Type":"application/x-www-form-urlencoded",
            "Accept":"application/json"},method="POST")
        valid_status="IAM_AUTH_VERIFIED"
        note="IBM IAM token issued. watsonx project permissions and inference NOT verified."
    try:
        with client.open(req,timeout=8) as response:
            if response.status!=200:return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
            raw=response.read(32769)
        if len(raw)>32768:
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
        result=json.loads(raw)
        if not isinstance(result,dict):
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
        if provider=="huggingface" and not isinstance(result.get("name"),str):
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
        if provider=="ollama_cloud" and not isinstance(result.get("data"),list):
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
        if provider=="ollama_cloud":
            # Public /v1/models returns canonical direct-API IDs; "-cloud" is
            # an Ollama app/CLI convenience tag, NOT the direct API model ID.
            # The check must not claim model entitlement or account auth.
            listed = {entry.get("id") for entry in result["data"]
                      if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
            model = config["model"]
            if model.endswith("-cloud") and model[:-6] in listed:
                return {"provider":provider,"status":"MODEL_ID_MODE_MISMATCH",
                        "detail":"The saved -cloud suffix is for the Ollama app/CLI. Direct API uses the corresponding name without -cloud. Select local in Brain Bay, update the saved ID with the existing encrypted key, and then explicitly select remote again. No inference was performed."}
            if model not in listed:
                return {"provider":provider,"status":"MODEL_NOT_LISTED",
                        "detail":"Saved model ID is not in Ollama's public direct-API inventory. No account entitlement or inference was verified."}
        if provider=="ibm_watsonx" and not isinstance(result.get("access_token"),str):
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
        return {"provider":provider,"status":valid_status,"detail":note}
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403):
            return {"provider":provider,"status":"AUTH_REJECTED"}
        return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
    except Exception:
        return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED"}
