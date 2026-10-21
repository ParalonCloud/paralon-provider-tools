#!/usr/bin/env python3
"""Prometheus exporter for your Paralon nodes.

Reads GET /api/v1/nodes from the Paralon provider API (one call for the whole
fleet) and serves the result in Prometheus text format on :9817/metrics:
every node's state, availability and price, and the last reading of each GPU
(load, temperature, power, VRAM) and of the host (CPU, memory).

Needs only the Python 3 standard library. Configure with:
  PARALON_API_KEY   a key with the My nodes permission (required)
  PARALON_BASE_URL  default https://paraloncloud.com/api/v1
  PORT              default 9817
  CACHE_SECONDS     default 30: scrapes within this window reuse one API call

Docs: https://paraloncloud.com/docs/provider-api
"""
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API = os.environ.get("PARALON_BASE_URL", "https://paraloncloud.com/api/v1")
KEY = os.environ["PARALON_API_KEY"]
PORT = int(os.environ.get("PORT", "9817"))
CACHE = int(os.environ.get("CACHE_SECONDS", "30"))
STATES = ["available", "rented", "paused", "not_verified", "not_ready", "offline"]

_lock = threading.Lock()
_cache = {"at": 0.0, "body": ""}


def esc(v) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def fetch_nodes() -> list:
    req = urllib.request.Request(f"{API}/nodes", headers={"Authorization": f"Bearer {KEY}", "User-Agent": "paralon-exporter/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["nodes"]


def render() -> str:
    out = []

    def metric(name, help_, type_="gauge"):
        out.append(f"# HELP {name} {help_}")
        out.append(f"# TYPE {name} {type_}")

    t0 = time.time()
    try:
        nodes = fetch_nodes()
        ok = 1
    except Exception:
        nodes, ok = [], 0
    took = time.time() - t0

    metric("paralon_api_up", "1 if the last call to the Paralon API succeeded")
    out.append(f"paralon_api_up {ok}")
    metric("paralon_api_seconds", "Duration of the last call to GET /nodes")
    out.append(f"paralon_api_seconds {took:.3f}")

    metric("paralon_node_info", "One series per node, value 1, with its name, type and GPU model")
    metric("paralon_node_state", "1 for the node's current state, 0 for the others")
    metric("paralon_node_available", "1 when the node is on the market")
    metric("paralon_node_online", "1 when the node's agent is connected")
    metric("paralon_node_price_usd_per_hour", "What a new rental of the node pays per hour")
    metric("paralon_node_metrics_age_seconds", "Age of the node's last live reading")
    metric("paralon_gpu_utilization_percent", "GPU load from the last reading")
    metric("paralon_gpu_temperature_celsius", "GPU temperature from the last reading")
    metric("paralon_gpu_power_watts", "GPU power draw from the last reading")
    metric("paralon_gpu_memory_used_mb", "GPU memory in use")
    metric("paralon_gpu_memory_free_mb", "GPU memory free")
    metric("paralon_host_cpu_percent", "Host CPU load")
    metric("paralon_host_memory_used_mb", "Host memory in use")

    now = time.time()
    for n in nodes:
        lab = f'node="{esc(n["id"])}",name="{esc(n["name"])}"'
        model = (n.get("gpus") or [{}])[0].get("model", "")
        out.append(f'paralon_node_info{{{lab},type="{esc(n.get("type", ""))}",gpu="{esc(model)}"}} 1')
        for s in STATES:
            out.append(f'paralon_node_state{{{lab},state="{s}"}} {1 if n["state"] == s else 0}')
        out.append(f'paralon_node_available{{{lab}}} {1 if n.get("available") else 0}')
        out.append(f'paralon_node_online{{{lab}}} {1 if n.get("online") else 0}')
        price = (n.get("price") or {}).get("renter_pays")
        if price is not None:
            out.append(f"paralon_node_price_usd_per_hour{{{lab}}} {price}")
        m = n.get("metrics")
        if not m:
            continue
        try:
            at = time.mktime(time.strptime(m["at"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            out.append(f"paralon_node_metrics_age_seconds{{{lab}}} {max(0, now - at):.0f}")
        except (KeyError, ValueError):
            pass
        for i, g in enumerate(m.get("gpus") or []):
            gl = f'{lab},gpu="{i}"'
            for key, name in [("utilization_pct", "paralon_gpu_utilization_percent"), ("temperature_c", "paralon_gpu_temperature_celsius"),
                              ("power_w", "paralon_gpu_power_watts"), ("vram_used_mb", "paralon_gpu_memory_used_mb"), ("vram_free_mb", "paralon_gpu_memory_free_mb")]:
                if g.get(key) is not None:
                    out.append(f"{name}{{{gl}}} {g[key]}")
        if m.get("cpu_pct") is not None:
            out.append(f"paralon_host_cpu_percent{{{lab}}} {m['cpu_pct']}")
        if m.get("memory_used_mb") is not None:
            out.append(f"paralon_host_memory_used_mb{{{lab}}} {m['memory_used_mb']}")
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with _lock:
            if time.time() - _cache["at"] > CACHE:
                _cache["body"], _cache["at"] = render(), time.time()
            body = _cache["body"].encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"paralon exporter on :{PORT}/metrics", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
