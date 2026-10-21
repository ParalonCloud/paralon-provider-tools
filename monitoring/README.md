# Fleet monitoring: Prometheus + Grafana

Every GPU you host on Paralon in one Grafana dashboard: temperature, load, power and memory over time, which nodes are rented, offline or waiting, and alert rules for a hot GPU or a node that dropped. Nothing is installed on the GPU machines: the Paralon agent already reports a reading about once a minute, and the exporter reads the whole fleet from the provider API in one call.

```bash
export PARALON_API_KEY=prlc_your_key   # My nodes permission, nothing else
docker compose up -d
```

Grafana: http://localhost:3000 (first login `admin` / `admin`), dashboard **Paralon fleet**. Prometheus: http://localhost:9090.

| File | What it is |
| --- | --- |
| `paralon_exporter.py` | standard-library Python exporter on `:9817/metrics`, one API call per scrape (cached 30 s) |
| `prometheus.yml` | scrapes every 60 s, loads `alerts.yml` |
| `alerts.yml` | `GPUHot` (≥ 85 °C for 5 min), `NodeOffline`, `NodeNotRentable`, `ParalonAPIDown` |
| `grafana/` | datasource, dashboard provider and the dashboard |

The rules fire in Prometheus; add Alertmanager or Grafana alerting to be notified. Full guide: https://paraloncloud.com/resources/gpu-fleet-temperature-grafana
