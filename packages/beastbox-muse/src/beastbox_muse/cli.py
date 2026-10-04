"""``beastbox muse`` and ``beastbox-muse`` command line."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .privacy import MuseKitError
from .schema import DISCLAIMER
from .service import (
    connect_ble_window,
    connect_lsl_window,
    demo_payload,
    discover_live,
    record_snapshots,
    run_simulate,
    status,
)
from .simulate import window as simulated_window


def _live_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--source", choices=["auto", "ble", "lsl"], default="auto")
    parser.add_argument("--address", default="", help="BLE address; scanned when omitted")
    parser.add_argument("--name", default="")


def add_commands(commands: argparse._SubParsersAction) -> None:
    connect = commands.add_parser("connect", help="find a headband and print one derived window")
    _live_flags(connect)
    connect.add_argument("--model", choices=["auto", "legacy", "athena"], default="auto")

    commands.add_parser("status", help="show the fallback order and which libraries are installed")

    record = commands.add_parser("record", help="append derived features to a local JSONL file")
    _live_flags(record)
    record.add_argument("--model", choices=["auto", "legacy", "athena"], default="auto")
    record.add_argument("--out", type=Path, default=Path("muse-session.jsonl"))
    record.add_argument("--seconds", type=int, default=1, help="one derived window per second, up to 120")
    record.add_argument("--raw", action="store_true", help="also write raw EEG to a local .raw.jsonl file")

    simulate = commands.add_parser("simulate", help="drive bio inputs from the synthetic headband")
    simulate.add_argument("--consent", action="store_true")
    simulate.add_argument("--seconds", type=int, default=1)
    simulate.add_argument("--demo", action="store_true", help="print the companion mock window driving bio inputs")
    simulate.add_argument("--out", type=Path)
    simulate.add_argument("--raw", action="store_true")


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    muse = subparsers.add_parser(
        "muse",
        help="Muse headband kit: wellness and game signals, not medical",
        description=DISCLAIMER,
    )
    add_commands(muse.add_subparsers(dest="muse_cmd", required=True))


def handle_args(args: argparse.Namespace) -> dict:
    command = args.muse_cmd
    if command == "status":
        return status()
    if command == "simulate":
        return _simulate(args)
    if command in {"connect", "record"}:
        return _live(args)
    raise MuseKitError("unknown muse command")


def _simulate(args: argparse.Namespace) -> dict:
    snapshots = run_simulate(consent=args.consent is True, windows=args.seconds)
    payload = demo_payload(snapshots[0])
    payload["windows"] = len(snapshots)
    if len(snapshots) > 1:
        payload["latest_traits"] = snapshots[-1]["traits"]
    if args.out is not None or args.raw:
        raw = [simulated_window(index) for index in range(len(snapshots))] if args.raw else None
        payload["record"] = record_snapshots(snapshots, args.out or Path("muse-session.jsonl"), raw_samples=raw)
    return payload


def _live(args: argparse.Namespace) -> dict:
    if args.consent is not True:
        raise MuseKitError(
            "Explicit consent is required. Re-run with --consent after the wearer agrees. " + DISCLAIMER
        )
    windows = args.seconds if args.muse_cmd == "record" else 1
    if not isinstance(windows, int) or isinstance(windows, bool) or not 1 <= windows <= 120:
        raise MuseKitError("seconds must be an integer from 1 to 120")
    collected = []
    raw_windows: list[list[float]] = []
    for _ in range(windows):
        snapshot, samples = _one_live_window(args)
        collected.append(snapshot)
        if samples is not None:
            raw_windows.append(samples)
    if args.muse_cmd == "connect":
        return demo_payload(collected[0])
    if args.raw and len(raw_windows) != len(collected):
        raise MuseKitError(
            "This transport published derived bands without raw samples. "
            "Refusing to write an empty raw file. Derived features were not saved."
        )
    saved = record_snapshots(
        collected,
        args.out,
        raw_samples=raw_windows if args.raw else None,
    )
    return {
        "disclaimer": DISCLAIMER,
        "windows": len(collected),
        "latest": demo_payload(collected[-1]),
        "record": saved,
    }


def _one_live_window(args: argparse.Namespace) -> tuple[dict, list[float] | None]:
    from .bio_map import snapshot_from_samples

    source = args.source
    if source == "lsl":
        _family, packed = connect_lsl_window()
        return packed["snapshot"], packed["samples"]
    if source == "ble" or (source == "auto" and args.address):
        address, name = _ble_target(args)
        family, samples = connect_ble_window(address, name=name, model=args.model)
        snapshot = snapshot_from_samples(samples, transport="ble", model_family=family, simulated=False)
        return snapshot, samples
    found = discover_live(preference="auto")
    if found.get("transport") == "lsl":
        _family, packed = connect_lsl_window()
        return packed["snapshot"], packed["samples"]
    if found.get("transport") == "ble":
        family, samples = connect_ble_window(found["address"], name=found.get("name", ""), model=args.model)
        snapshot = snapshot_from_samples(samples, transport="ble", model_family=family, simulated=False)
        return snapshot, samples
    raise MuseKitError(json.dumps({
        "disclaimer": DISCLAIMER,
        "transport": None,
        "tried": found.get("tried", []),
        "next": found.get("next"),
    }, sort_keys=True))


def _ble_target(args: argparse.Namespace) -> tuple[str, str]:
    if args.address:
        return args.address, args.name
    found = discover_live(preference="ble")
    if found.get("transport") != "ble":
        raise MuseKitError(json.dumps({
            "disclaimer": DISCLAIMER,
            "transport": None,
            "tried": found.get("tried", []),
            "next": found.get("next"),
        }, sort_keys=True))
    return found["address"], args.name or found.get("name", "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="beastbox-muse", description=DISCLAIMER)
    add_commands(parser.add_subparsers(dest="muse_cmd", required=True))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(handle_args(args), indent=2, sort_keys=True))
        return 0
    except MuseKitError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
