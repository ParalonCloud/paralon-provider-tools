# Paralon provider tools

Open-source tools for GPU providers on [ParalonCloud](https://paraloncloud.com), built on the [Paralon provider API](https://paraloncloud.com/docs/provider-api). Each one needs only a Paralon API key with the **My nodes** permission (Console → API keys), in `PARALON_API_KEY`.

| Tool | What it does | Guide |
| --- | --- | --- |
| [`monitoring/`](monitoring) | Prometheus exporter, Grafana dashboard and alert rules for every GPU you host: temperature, load, power, memory, node states. One `docker compose up -d` | [Every GPU in your fleet in Grafana](https://paraloncloud.com/resources/gpu-fleet-temperature-grafana) |
| [`multi-marketplace/`](multi-marketplace) | Keep one machine listed on Paralon and another marketplace without renting it twice | [List one GPU machine on several marketplaces](https://paraloncloud.com/resources/list-gpu-on-multiple-marketplaces) |
| [`auto-pricing/`](auto-pricing) | Move each node's price with its own demand, inside a floor and ceiling you set | [Price your GPUs from their own demand](https://paraloncloud.com/resources/automatic-gpu-pricing) |

To manage your nodes in plain language from Claude Code instead, see [paralon-skills](https://github.com/ParalonCloud/paralon-skills); for any MCP client, [paralon-mcp](https://github.com/ParalonCloud/paralon-mcp).

## Safety

The tools only use your own key against your own nodes. A key with only **My nodes** cannot rent GPUs, call models or spend credits, and no key can request a payout, change where payouts go or delete a node. Give each tool its own key.

## Links

- Provider API docs: https://paraloncloud.com/docs/provider-api
- Provider API announcement: https://paraloncloud.com/resources/gpu-provider-api-run-your-fleet

MIT
