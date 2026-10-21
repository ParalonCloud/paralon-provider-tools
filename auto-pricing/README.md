# Prices that follow each node's demand

`auto_price.py` checks every node every 15 minutes: idle on the market for 6 hours, the price goes down 5%; re-rented within an hour of the last rental, it goes up 5% for the next rental; never outside your floor and ceiling (80% to 150% of the node's default by default) or Paralon's 50% to 300% range. Spot nodes are left alone. A running rental always keeps its price.

```bash
pip install requests
export PARALON_API_KEY=prlc_your_key
python3 auto_price.py --dry-run   # prints what it would do, changes nothing
python3 auto_price.py             # runs, keeps its memory in auto_price_state.json
python3 simulate.py               # replays a made-up week, no API call
```

Knobs: `IDLE_HOURS`, `QUICK_HOURS`, `STEP`, `FLOOR`, `CEILING`, `MARKET_JSON` (+ `MARKET_BAND`), `CHECK_MINUTES`. Full guide: https://paraloncloud.com/resources/automatic-gpu-pricing
