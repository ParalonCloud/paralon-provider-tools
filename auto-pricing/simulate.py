#!/usr/bin/env python3
"""Replay a made-up week of one RTX 4090 node through auto_price.decide() and
print every price change. No API call is made."""
from auto_price import CFG, decide

H = 3600
node = {"id": "n1", "name": "rig-1", "spot": False, "gpus": [{"model": "NVIDIA GeForce RTX 4090"}],
        "price": {"default": 0.54, "min": 0.27, "max": 1.62, "custom": None}}
# (hour, state the API reports)
timeline = [(0, "available"), (3, "available"), (6, "available"), (12, "available"), (18, "available"),
            (19, "rented"), (31, "available"), (31.5, "rented"), (55, "available"), (55.5, "rented"),
            (80, "available"), (86, "available"), (92, "available"), (98, "available"), (104, "available")]
st = {}
for hour, state in timeline:
    node["state"] = state
    new, why, st = decide(node, st, hour * H, CFG, {})
    cur = node["price"]["custom"] or node["price"]["default"]
    if new is not None:
        node["price"]["custom"] = new
        print(f"h{hour:>5}  {state:<9}  ${cur:.2f} -> ${new:.2f}  {why}")
    else:
        print(f"h{hour:>5}  {state:<9}  ${cur:.2f}           {why}")
