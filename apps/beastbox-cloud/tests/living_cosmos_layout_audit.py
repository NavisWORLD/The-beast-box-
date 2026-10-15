"""Layout acceptance audit for the public Beast Box routes.

Real Chromium and WebKit (Playwright) at the Living Cosmos target sizes:
320/375/390/430 portrait phones, phone landscape, tablet and desktop.
For every route it records (no owner data, sensors, cloud writes or models):

* horizontal document overflow and the elements that cause it,
* visible text that escapes the viewport,
* touch targets under 24 CSS px (WCAG 2.5.8) and under 44 px on touch sizes,
* interactive controls covered by a fixed/sticky layer at any scroll position,
* uncaught page errors.

Usage: python tests/living_cosmos_layout_audit.py [--base URL] [--out DIR]
       [--engines chromium,webkit] [--routes /,/beast-cage] [--sizes 390x844]
Exit status is non-zero when any blocking defect (overflow, escaped text,
covered control, sub-24 px target, page error) is found, unless --report-only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROUTES = ["/", "/spark/index.html", "/beast-cage", "/beast-cage/talk", "/sol-game", "/brain-bay",
          "/research", "/workspace", "/settings", "/try", "/privacy"]
SIZES = [("phone-320", 320, 720, True), ("phone-375", 375, 812, True), ("phone-390", 390, 844, True),
         ("phone-430", 430, 932, True), ("phone-landscape", 844, 390, True), ("tablet", 820, 1180, True),
         ("desktop", 1440, 900, False)]

PROBE = r"""
() => {
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const INTERACTIVE = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=tab],[role=switch],[role=checkbox],[role=link]';
  const describe = el => {
    if (!el) return null;
    const id = el.id ? '#' + el.id : '';
    const cls = typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '';
    const label = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
    return el.tagName.toLowerCase() + id + cls + (label ? ' "' + label + '"' : '');
  };
  const shown = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0.5 && r.height > 0.5;
  };
  const clippedByAncestor = (el, includeSelf = false) => {
    for (let p = includeSelf ? el : el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.clip && s.clip !== 'auto') return true;
      if (s.clipPath && s.clipPath !== 'none') return true;
      if (/(hidden|clip|auto|scroll)/.test(s.overflowX) || /(hidden|clip)/.test(s.overflow)) {
        const pr = p.getBoundingClientRect();
        if (pr.right <= vw + 1 && pr.left >= -1) return true;
      }
    }
    return false;
  };
  const floatingAncestor = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const p = getComputedStyle(n).position;
      if (p === 'fixed' || p === 'sticky') return n;
    }
    return null;
  };
  const de = document.documentElement;
  const overflowX = Math.max(0, de.scrollWidth - vw);
  const offenders = [];
  if (overflowX > 1) {
    for (const el of document.body.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      if ((r.right > vw + 1 || r.left < -1) && !clippedByAncestor(el)) offenders.push({el: describe(el), left: Math.round(r.left), right: Math.round(r.right)});
      if (offenders.length >= 8) break;
    }
  }
  const textEscapes = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.textContent.trim() || !node.parentElement || !shown(node.parentElement)) continue;
    const range = document.createRange(); range.selectNodeContents(node);
    const r = range.getBoundingClientRect();
    if (r.width < 1) continue;
    if ((r.right > vw + 2 || r.left < -2) && !clippedByAncestor(node.parentElement, true)) {
      textEscapes.push({el: describe(node.parentElement), text: node.textContent.trim().slice(0, 50), left: Math.round(r.left), right: Math.round(r.right)});
      if (textEscapes.length >= 8) break;
    }
  }
  const tiny = [], small = [];
  for (const el of document.querySelectorAll(INTERACTIVE)) {
    if (!shown(el) || el.closest('[aria-hidden=true]') || el.disabled) continue;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    const inlineLink = el.tagName === 'A' && s.display === 'inline' && el.parentElement && (el.parentElement.textContent || '').trim().length > (el.textContent || '').trim().length + 12;
    if (inlineLink) continue;
    const box = {el: describe(el), w: Math.round(r.width), h: Math.round(r.height)};
    if (Math.min(r.width, r.height) < 24) tiny.push(box); else if (Math.min(r.width, r.height) < 44) small.push(box);
  }
  return {vw, vh, scrollHeight: de.scrollHeight, overflowX, offenders, textEscapes, tiny, small, title: document.title};
}
"""

COVERED = r"""
() => {
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const INTERACTIVE = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=tab],[role=switch],[role=checkbox]';
  const describe = el => {
    if (!el) return null;
    const id = el.id ? '#' + el.id : '';
    const cls = typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '';
    const label = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
    return el.tagName.toLowerCase() + id + cls + (label ? ' "' + label + '"' : '');
  };
  const floatingAncestor = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const p = getComputedStyle(n).position;
      if (p === 'fixed' || p === 'sticky') return n;
    }
    return null;
  };
  const out = [];
  for (const el of document.querySelectorAll(INTERACTIVE)) {
    if (el.closest('[aria-hidden=true]') || el.disabled) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.pointerEvents === 'none') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom <= 0 || r.top >= vh || r.right <= 0 || r.left >= vw) continue;
    const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2)), cy = Math.min(vh - 1, Math.max(0, r.top + r.height / 2));
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || hit === el || el.contains(hit) || hit.contains(el)) continue;
    const cover = floatingAncestor(hit);
    if (!cover || cover.contains(el) || floatingAncestor(el) === cover) continue;
    out.push({control: describe(el), coveredBy: describe(cover), at: [Math.round(cx), Math.round(cy)]});
  }
  return out;
}
"""


def run(base: str, out: Path, engines: list[str], routes: list[str], sizes: list[tuple], report_only: bool) -> int:
    out.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        for engine in engines:
            launcher = getattr(p, engine)
            kwargs = {"headless": True}
            if engine == "chromium":
                kwargs["args"] = ["--no-sandbox", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"]
            browser = launcher.launch(**kwargs)
            for label, width, height, touch in sizes:
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1,
                                              is_mobile=touch and width < 900, has_touch=touch)
                for route in routes:
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("pageerror", lambda error, sink=errors: sink.append(str(error)[:200]))
                    started = time.time()
                    status = None
                    try:
                        response = page.goto(base + route, wait_until="load", timeout=45000)
                        status = response.status if response else None
                        page.wait_for_timeout(2500)
                        probe = page.evaluate(PROBE)
                        covered = []
                        seen = set()
                        steps = min(6, max(1, int(probe["scrollHeight"] / max(1, height * 0.8)) + 1))
                        for step in range(steps):
                            page.evaluate(f"window.scrollTo(0,{int(step * height * 0.8)})")
                            page.wait_for_timeout(250)
                            for item in page.evaluate(COVERED):
                                key = (item["control"], item["coveredBy"])
                                if key not in seen:
                                    seen.add(key)
                                    covered.append(item)
                        page.evaluate("window.scrollTo(0,0)")
                        page.wait_for_timeout(200)
                        slug = re.sub(r"[^a-z0-9]+", "-", route.lower()).strip("-") or "home"
                        shot = out / f"{engine}-{label}-{slug}.png"
                        page.screenshot(path=str(shot), animations="disabled")
                    except Exception as error:  # recorded as a failure, never silently skipped
                        probe = {"error": str(error)[:300]}
                        covered = []
                        shot = None
                    record = {"engine": engine, "size": label, "viewport": [width, height], "route": route, "status": status,
                              "ms": int((time.time() - started) * 1000), "pageErrors": errors[:5], "covered": covered[:12],
                              "screenshot": str(shot) if shot else None, **probe}
                    record["blocking"] = bool(record.get("error") or (status or 0) >= 400 or record.get("overflowX", 0) > 1
                                              or record.get("textEscapes") or covered or record.get("tiny") or errors)
                    records.append(record)
                    print(json.dumps({k: record.get(k) for k in ("engine", "size", "route", "status", "overflowX", "blocking")}), flush=True)
                    page.close()
                context.close()
            browser.close()
    summary = {
        "schema": "beastbox-layout-audit-v1",
        "base": base,
        "engines": engines,
        "pages": len(records),
        "blocking_pages": sum(1 for r in records if r["blocking"]),
        "overflow_pages": sum(1 for r in records if r.get("overflowX", 0) > 1),
        "text_escape_pages": sum(1 for r in records if r.get("textEscapes")),
        "covered_pages": sum(1 for r in records if r.get("covered")),
        "tiny_target_pages": sum(1 for r in records if r.get("tiny")),
        "page_error_pages": sum(1 for r in records if r.get("pageErrors")),
        "load_failures": sum(1 for r in records if r.get("error") or (r.get("status") or 0) >= 400),
        "physical_device": False,
        "note": "Automated Playwright engines with emulated viewports; not a physical iPhone or Android device.",
    }
    (out / "layout-audit.json").write_text(json.dumps({"summary": summary, "records": records}, indent=1))
    print("LAYOUT_AUDIT_SUMMARY", json.dumps(summary))
    return 0 if report_only or summary["blocking_pages"] == 0 else 1


def parse_sizes(value: str | None):
    if not value:
        return SIZES
    wanted = value.split(",")
    picked = [s for s in SIZES if s[0] in wanted]
    for item in wanted:
        match = re.fullmatch(r"(\d+)x(\d+)", item)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            picked.append((f"custom-{w}x{h}", w, h, w < 900))
    return picked


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("BEAST_AUDIT_BASE", "http://127.0.0.1:3100"))
    parser.add_argument("--out", default="browser-evidence/layout-audit")
    parser.add_argument("--engines", default="chromium,webkit")
    parser.add_argument("--routes", default=",".join(ROUTES))
    parser.add_argument("--sizes", default=None)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    sys.exit(run(args.base.rstrip("/"), Path(args.out), args.engines.split(","), args.routes.split(","),
                 parse_sizes(args.sizes), args.report_only))
