#!/usr/bin/env python3
"""Keep one GPU machine listed on Paralon and on another marketplace without
renting it twice.

Every POLL seconds it asks two questions:
  1. Is the machine rented on Paralon?          (GET /nodes/{id}, state == "rented")
  2. Is the machine busy with the other market? (busy_elsewhere(), you fill it in)

and keeps each side's availability in step with the other:
  - rented on Paralon      -> take it off the other marketplace
  - busy elsewhere         -> take it off Paralon (PATCH available=false)
  - free on both           -> put it back on both

Both rented at once (each started inside the same poll window) is the one
case left; see resolve_conflict().

Needs: Python 3.8+, `pip install requests`, a Paralon key with the My nodes
permission in PARALON_API_KEY, and the node id in PARALON_NODE_ID.
Docs: https://paraloncloud.com/docs/provider-api
"""
import json
import os
import subprocess
import sys
import time

import requests

API = os.environ.get("PARALON_BASE_URL", "https://paraloncloud.com/api/v1")
KEY = os.environ["PARALON_API_KEY"]
NODE = os.environ["PARALON_NODE_ID"]
POLL = int(os.environ.get("POLL_SECONDS", "15"))
H = {"Authorization": f"Bearer {KEY}"}


# ---------------------------------------------------------------- the other side

def busy_elsewhere() -> bool:
    """True while the other marketplace has a job on this machine.

    Pick the check that fits your setup:
    - its job containers:   docker ps --filter "label=<their label>" -q
    - its CLI or API:       ask whether this machine has an active rental
    - a file it writes:     os.path.exists("/run/other-market/busy")
    The default looks at a flag file, so the script can be tried safely.
    """
    return os.path.exists(os.environ.get("BUSY_FLAG", "/tmp/busy-elsewhere"))


def set_available_elsewhere(available: bool) -> None:
    """List or unlist the machine on the other marketplace.

    Put your marketplace's own command here (its CLI or API call to list or
    unlist this machine). The default only logs, so nothing changes until you
    fill it in.
    """
    cmd = os.environ.get("OTHER_LIST_CMD" if available else "OTHER_UNLIST_CMD")
    if cmd:
        subprocess.run(cmd, shell=True, check=False)
    log(f"other marketplace: {'list' if available else 'unlist'}" + ("" if cmd else " (no command set, only logged)"))


# ---------------------------------------------------------------- Paralon side

def paralon_node() -> dict:
    r = requests.get(f"{API}/nodes/{NODE}", headers=H, timeout=30)
    r.raise_for_status()
    return r.json()


def set_available_paralon(available: bool) -> dict:
    r = requests.patch(f"{API}/nodes/{NODE}", headers=H, json={"available": available}, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_conflict(node: dict) -> None:
    """Both marketplaces started a rental inside the same poll window.

    On a Paralon spot node, the clean way out is a reclaim: the Paralon renter
    gets two minutes' notice and is billed until it stops. On an on-demand
    node, a reclaim is not possible: let both finish if the machine can carry
    both, or end the other marketplace's job by its own rules.
    """
    if node.get("spot"):
        r = requests.post(f"{API}/nodes/{NODE}/reclaim", headers=H, timeout=30)
        log(f"conflict: reclaimed the Paralon spot rental ({r.status_code}): {r.json().get('reclaim')}")
    else:
        log("conflict: rented on both; on-demand rentals are not reclaimed, decide by hand")


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------- loop

def step(state: dict) -> None:
    node = paralon_node()
    rented_here = node["state"] == "rented"
    elsewhere = busy_elsewhere()

    if rented_here and elsewhere:
        resolve_conflict(node)
    elif rented_here:
        if state.get("other_listed", True):
            set_available_elsewhere(False)
            state["other_listed"] = False
    elif elsewhere:
        if node["available"]:
            set_available_paralon(False)
            log("busy elsewhere: off the Paralon market")
    else:
        if not node["available"]:
            set_available_paralon(True)
            log("free: back on the Paralon market")
        if not state.get("other_listed", True):
            set_available_elsewhere(True)
            state["other_listed"] = True


def main() -> None:
    state: dict = {}
    log(f"watching node {NODE} every {POLL}s")
    while True:
        try:
            step(state)
        except requests.RequestException as e:
            log(f"Paralon API error, retrying next poll: {e}")
        if "--once" in sys.argv:
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
