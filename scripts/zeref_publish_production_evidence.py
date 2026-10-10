"""Append actual production observations to the existing Zeref evidence chain.

Run only after inspecting the native screenshots. Never submits a provider job,
changes model weights, or mints a blockchain token.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from beastbox.persistent_substrate.ledger import StateEventLedger
from zeref_fresh_heart_live import OUT, stamp
from zeref_public_ledger_refresh import PUBLIC, refresh


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main(folder, video):
    combined = read(folder / "combined.json")
    physical, game = combined["hardware"], combined["production_game"]
    overlap = read(folder / "provider-verified-overlap.json")
    quota_before = read(folder / "quota-before.json")
    quota_after = read(folder / "quota-after.json")
    if (quota_before["already_consumed_seconds"] + 60 > 300 or
            quota_after["already_consumed_seconds"] > 300 or
            physical["max_qpu_seconds"] != 60 or physical["new_jobs_submitted"] != 1):
        raise ValueError("The authorized bounded Open Plan budget must be preserved")
    if (physical["job_status"] != "DONE" or physical["shots"] != 131072 or
            physical["qbeast_id"] != "bb-deada969" or
            physical["genesis_job_id"] != "db4q484vf2bc73cuuuag" or
            game["qbeast_id"] != "bb-deada969" or game["native_id"] != 0xdeada969 or
            len(game["conversation"]) != 3 or len(game["cage_observations"]) != 12 or
            len(overlap["turns"]) != 3 or
            not all(x["started_within_provider_execution"] and
                    x["completed_within_provider_execution"] for x in overlap["turns"])):
        raise ValueError("Completed identity-matched actual recording and provider overlap required")
    counts = physical["measurements"]
    if (any(sum(c.values()) != 32768 for c in counts.values()) or len(counts) != 4 or
            hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            != physical["counts_sha256"]):
        raise ValueError("Actual four-PUB counts and hash must agree")
    parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    began_at, ended_at = parse(overlap["running"]), parse(overlap["finished"])
    for turn in game["conversation"]:
        if (turn["provider"] != "rawrphos-local" or turn["model"] != "rawrphos-native" or
                turn["step"] != 14000 or turn["guest_stateless"] is not True or
                turn["checkpoint_sha256"] != "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5" or
                not turn["actual_model_reply"].strip() or
                not began_at <= parse(turn["started_utc"]) < parse(turn["completed_utc"]) <= ended_at):
            raise ValueError("Actual independently identified hosted model replies required")
    if game["browser_pageerrors"]:
        raise ValueError("Browser errors require review before publishing")
    assets = {
        "Zeref_live_recording.mp4": video,
        "Zeref_live_cage.png": folder / "browser/zeref-live-cage.png",
        "Zeref_live_game.png": folder / "browser/zeref-live-native.png",
        "Zeref_live_conversation.png": folder / "browser/zeref-live-conversation.png",
        "Zeref_live_native.sav": folder / "browser/zeref-live-native.sav",
    }
    for name, source in assets.items():
        if not source.is_file() or not source.stat().st_size:
            raise ValueError("Missing actual evidence asset: " + name)
        shutil.copyfile(source, PUBLIC / name)
    if (PUBLIC / "Zeref_live_native.sav").stat().st_size != 32768:
        raise ValueError("Native battery size changed")
    ledger = StateEventLedger(OUT / "quantum-ledger.jsonl")
    ledger.append("PRODUCTION_PHYSICAL_CONVERSATION_WORKLOAD_COMPLETED", physical, physical["observed_utc"])
    ledger.append("PRODUCTION_CAGE_OBSERVATIONS", {"qbeast_id":game["qbeast_id"],
                  "samples":game["cage_observations"]}, stamp())
    ledger.append("PRODUCTION_NATIVE_GAME_OBSERVED", {
        "qbeast_id":game["qbeast_id"],"native_id":game["native_id"],
        "native_seed":game["native_seed"],"actual_a_input":game["actual_a_input"],
        "movement_inputs":game["observed_movement_inputs"],
        "persisted_sram":game["persisted_native_state"],
        "native_save_sha256":sha(PUBLIC / "Zeref_live_native.sav"),
        "quest_completion_claimed":False},stamp())
    for turn in game["conversation"]:
        ledger.append("PRODUCTION_ACTUAL_HOSTED_MODEL_REPLY",turn,turn["completed_utc"])
    ledger.append("PROVIDER_TIMESTAMPS_VERIFIED_CONVERSATION_OVERLAP",overlap,stamp())
    ledger.append("ACTUAL_PRODUCTION_MEDIA_SEALED",{
        "file_sha256":{name:sha(PUBLIC/name) for name in assets},
        "video_origin":"ACTUAL_PLAYWRIGHT_PRODUCTION_BROWSER_RECORDING",
        "audio_track":"NONE; ORIGINAL_BROWSER_RECORDING_WAS_SILENT",
        "post_live_session_sha256":sha(folder/"browser/post-live-session.json")},stamp())
    began=sum(x["started_within_provider_execution"] for x in overlap["turns"])
    production={
        "schema":"beastbox-zeref-actual-production-recording-v1",
        "summary":f"Zeref was recorded in the deployed Cage and actual native GBA cartridge. Three real hosted model replies were retained; {began} requests began within IBM's provider execution interval.",
        "qbeast_id":game["qbeast_id"],"genesis_ibm_job_id":physical["genesis_job_id"],
        "additional_physical_probe":physical,
        "provider_verified_overlap":overlap,
        "video":"Zeref_live_recording.mp4", "video_audio":"SILENT_ACTUAL_BROWSER_CAPTURE",
        "video_sha256":sha(PUBLIC/"Zeref_live_recording.mp4"),
        "cage_observations":game["cage_observations"],
        "conversation":game["conversation"],
        "native_state":game["persisted_native_state"],
        "movement_inputs":game["observed_movement_inputs"],
        "native_input_source":"RECORDER_SCRIPTED_BUTTONS",
        "autonomous_model_gameplay_verified":False,
        "optical_consent":game["optical_consent"],
        "optical_qualification":"Optical consent remained false. No native pixel measurements were included. The second observer prompt described screen-signal types without actual pixel observations; that wording is not evidence of vision.",
        "game_frame_observations":game["game_frame_observations"],
        "native_battery_sha256":sha(PUBLIC/"Zeref_live_native.sav"),
        "quota_before":quota_before,
        "quota_after":quota_after,
        "azure_cosmos_db_writes_verified":0,"onchain_minted":False,
    }
    write(PUBLIC/"production-summary.json",production)
    summary=read(PUBLIC/"run-summary.json")
    summary["native_recording_status"]="ACTUAL_PRODUCTION_RECORDING_COMPLETE"
    summary["production_recording"]={"receipt":"production-summary.json","video":production["video"],
        "additional_ibm_job_id":physical["job_id"],"actual_hosted_turns":3,
        "requests_started_within_provider_execution":began}
    write(PUBLIC/"run-summary.json",summary)
    metadata=read(PUBLIC/"nft-metadata.json")
    metadata["properties"]["production_recording"]={
        "url":"https://www.beastboxcosmos.xyz/spark/zeref-live-20261010/production-summary.json",
        "video_sha256":production["video_sha256"],"additional_ibm_job_id":physical["job_id"],
        "actual_hosted_turns":3}
    write(PUBLIC/"nft-metadata.json",metadata)
    refresh("Actual production Cage, native cartridge, hosted replies and provider-verified physical overlap")
    print(json.dumps({"qbeast_id":game["qbeast_id"],"actual_turns":3,"overlap_started":began,
                      "additional_ibm_job_id":physical["job_id"]}))


if __name__=="__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
