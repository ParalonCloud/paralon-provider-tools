#!/usr/bin/env python3
"""Move each Paralon node's price with its own demand, inside limits you set.

The rule, per node, checked every CHECK_MINUTES:
  - idle on the market for IDLE_HOURS or more since the last change  -> lower by STEP
  - re-rented within QUICK_HOURS of the last rental ending            -> raise by STEP
  - otherwise                                                         -> keep the price
never below FLOOR x the node's default price nor above CEILING x it, and never
outside the range the API allows (50% to 300% of the default).

Optionally, MARKET_JSON points to a file of reference prices you trust, per
GPU model ({"NVIDIA GeForce RTX 4090": 0.60}); the price is then also kept
within MARKET_BAND of that reference.

State (when each node became idle, when its last rental ended) is kept in
STATE_FILE, because the API reports the current rental only.

Needs: Python 3.8+, `pip install requests`, a key with the My nodes permission
in PARALON_API_KEY. Run with --dry-run first: it prints what it would do.
Docs: https://paraloncloud.com/docs/provider-api
"""
import json
import math
import os
import sys
import time

import requests

API = os.environ.get("PARALON_BASE_URL", "https://paraloncloud.com/api/v1")
H = {"Authorization": f"Bearer {os.environ.get('PARALON_API_KEY', '')}"}
STATE_FILE = os.environ.get("STATE_FILE", "auto_price_state.json")

CFG = {
    "IDLE_HOURS": float(os.environ.get("IDLE_HOURS", "6")),
    "QUICK_HOURS": float(os.environ.get("QUICK_HOURS", "1")),
    "STEP": float(os.environ.get("STEP", "0.05")),        # 5% per change
    "FLOOR": float(os.environ.get("FLOOR", "0.8")),       # never below 80% of the default
    "CEILING": float(os.environ.get("CEILING", "1.5")),   # never above 150% of the default
    "MARKET_BAND": float(os.environ.get("MARKET_BAND", "0.15")),
}
CHECK_MINUTES = float(os.environ.get("CHECK_MINUTES", "15"))


def decide(node: dict, st: dict, now: float, cfg: dict, market: dict) -> tuple:
    """Pure: from the node as the API returns it and what we remembered about
    it, return (new_price or None to keep, reason, updated state)."""
    st = dict(st)
    price = node["price"]
    if node.get("spot") or price.get("default") is None:
        return None, "spot or unpriced: not managed", st
    default = price["default"]
    current = price["custom"] if price.get("custom") is not None else default
    lo = max(price.get("min", 0), default * cfg["FLOOR"])
    hi = min(price.get("max", 1e9), default * cfg["CEILING"])
    ref = market.get((node.get("gpus") or [{}])[0].get("model", ""))
    if ref:
        lo = max(lo, ref * (1 - cfg["MARKET_BAND"]))
        hi = min(hi, ref * (1 + cfg["MARKET_BAND"]))

    lo, hi = math.ceil(lo * 100) / 100, math.floor(hi * 100) / 100  # whole cents, inside the limits

    state = node["state"]
    prev = st.get("state")
    if state == "rented":
        if prev != "rented":
            quick = st.get("last_rental_end") is not None and now - st["last_rental_end"] <= cfg["QUICK_HOURS"] * 3600
            st.update(state="rented", idle_since=None)
            if quick and current < hi:
                new = round(min(hi, current * (1 + cfg["STEP"])), 2)
                return new, f"re-rented within {cfg['QUICK_HOURS']:g} h: +{cfg['STEP']:.0%} for the next rental", st
        return None, "rented: keep", st

    if prev == "rented":
        st["last_rental_end"] = now
    if state != "available":
        st.update(state=state, idle_since=None)
        return None, f"{state}: not on the market, keep", st

    st["state"] = "available"
    if st.get("idle_since") is None:
        st["idle_since"] = now
    idle_h = (now - st["idle_since"]) / 3600
    if idle_h >= cfg["IDLE_HOURS"] and current > lo:
        new = round(max(lo, current * (1 - cfg["STEP"])), 2)
        st["idle_since"] = now  # wait a full IDLE_HOURS before the next step
        return new, f"idle {idle_h:.1f} h: -{cfg['STEP']:.0%}", st
    if current < lo or current > hi:
        return round(min(hi, max(lo, current)), 2), "outside your limits: brought back inside", st
    return None, f"available, idle {idle_h:.1f} h: keep", st


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def run_once(dry: bool, market: dict) -> None:
    state = load(STATE_FILE, {})
    nodes = requests.get(f"{API}/nodes", headers=H, timeout=30).json()["nodes"]
    now = time.time()
    for n in nodes:
        new, why, state[n["id"]] = decide(n, state.get(n["id"], {}), now, CFG, market)
        cur = n["price"].get("custom") or n["price"].get("default") or "-"
        line = f"{n['name']:<20} {n['state']:<12} ${cur}/h  {why}"
        if new is not None and new != cur:
            line += f"  -> ${new}/h"
            if not dry:
                r = requests.patch(f"{API}/nodes/{n['id']}", headers=H, json={"price_per_hour": new}, timeout=30)
                line += "" if r.ok else f"  (refused: {r.json().get('message')})"
        print(time.strftime("%H:%M:%S"), line, flush=True)
    if not dry:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    market = load(os.environ["MARKET_JSON"], {}) if os.environ.get("MARKET_JSON") else {}
    while True:
        run_once(dry, market)
        if dry or "--once" in sys.argv:
            break
        time.sleep(CHECK_MINUTES * 60)
