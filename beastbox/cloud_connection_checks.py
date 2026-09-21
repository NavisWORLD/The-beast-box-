"""Explicit owner-initiated read-only connection checks. No inference or quantum jobs.

Never expose remote response bodies, tokens, URL queries or exception strings.
Only fixed HTTPS provider endpoints are used (no arbitrary user-supplied URLs).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from .cloud_connections import ConnectionError

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ConnectionError("provider verification refused an HTTP redirect")


def verify_connection(provider: str, record: dict, opener=None) -> dict:
    """Read-only check; a valid token alone never proves inference or storage writes."""
    config,secret=record["config"],record["secret"]
    if provider=="ibm_quantum":
        return {"provider":provider,"status":"NOT_TESTED","detail":"IBM Quantum instance and job permissions require a separate authorized integration."}
    if provider=="azure_blob":
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            return {"provider":provider,"status":"NOT_TESTED","detail":"Azure Blob SDK not installed on durable host."}
        try:
            base="https://"+config["account"]+".blob.core.windows.net"
            client=BlobServiceClient(account_url=base,credential=secret)
            client.get_container_client(config["container"]).get_container_properties(
                timeout=5,connection_timeout=5,read_timeout=5)
            return {"provider":provider,"status":"CONTAINER_READ_VERIFIED",
                    "detail":"Read access verified; object writes and retention have not been tested."}
        except Exception:
            return {"provider":provider,"status":"REMOTE_UNAVAILABLE_OR_REJECTED",
                    "detail":"Azure container check failed; no storage-write claim."}
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
