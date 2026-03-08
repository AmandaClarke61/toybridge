---
name: toybridge
description: Control any BLE toy that has been reverse-engineered and connected via the ToyBridge server. Calls a local HTTP API to send vibrate/stop commands. Requires the ToyBridge server running on the same machine.
metadata: {"openclaw": {"os": ["darwin"]}}
---

# ToyBridge — Universal BLE Toy Control

Control **any BLE toy** through OpenClaw, as long as you have the [ToyBridge](https://github.com/AmandaClarke61/toybridge) server running.

This skill is for devices that are **not supported by Buttplug.io/Intiface** — devices with proprietary or unknown protocols that you've reverse-engineered yourself using the ToyBridge toolkit.

> If your device IS supported by Buttplug.io, use the `intiface-control` skill instead — it's easier.

---

## Prerequisites

1. You've reverse-engineered your device's BLE protocol using [ToyBridge](https://github.com/AmandaClarke61/toybridge)
2. You've configured `4-bridge/ble_worker.py` for your device
3. The ToyBridge server is running: `uv run 4-bridge/server.py`

See the [full setup guide](https://github.com/AmandaClarke61/toybridge) for step-by-step instructions.

---

## Commands the agent will use

### Vibrate at intensity

```bash
curl -s -X POST http://host.docker.internal:8888/vibrate \
  -H "Content-Type: application/json" \
  -d '{"intensity": 60}'
```

`intensity`: 0–100 (0 = stop)

### Stop immediately

```bash
curl -s -X POST http://host.docker.internal:8888/stop
```

### Check status

```bash
curl -s http://host.docker.internal:8888/status
```

> If OpenClaw runs natively (not in Docker), replace `host.docker.internal` with `localhost`.

---

## Intensity guide

| Range  | Feel    |
|--------|---------|
| 1–20   | Gentle  |
| 30–50  | Medium  |
| 60–80  | Strong  |
| 90–100 | Maximum |

---

## Preset patterns

| Pattern | What it does |
|---------|-------------|
| `pulse` | Bursts of 80%, 5 times |
| `wave`  | Ramp up 20→100%, then back down, x2 |
| `tease` | 30% → 70% → 100%, escalating, then stop |

To run a pattern:

```bash
curl -s -X POST http://host.docker.internal:8888/vibrate \
  -H "Content-Type: application/json" \
  -d '{"pattern": "wave"}'
```

---

## Agent rules

- Always stop (intensity 0) after a timed session unless user says to keep going
- Do **not** use the `notify` tool — use `bash` with `curl`
- Replace `host.docker.internal` with `localhost` if OpenClaw is not in Docker

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` | Make sure `uv run 4-bridge/server.py` is running |
| Device doesn't respond | Check your device config in `ble_worker.py` |
| Wrong intensity | Values are clamped to 0–100 |
