---
name: venus-ble-vibrator
description: Control a Venus (Cachito) BLE vibrator from natural language. Tells the agent how to call a local HTTP server that broadcasts BLE commands to the toy via macOS CoreBluetooth. Requires hardware setup — see README below before installing.
metadata: {"openclaw": {"os": ["darwin"]}}
---

# Venus BLE Vibrator Control

Control a **Venus / Cachito BLE vibrator** using natural language through OpenClaw. The agent calls a local HTTP API which broadcasts BLE advertisements to the toy.

> ⚠️ **macOS only.** The server uses CoreBluetooth (Apple-only). Linux/Windows not supported.

---

## What you need

**Hardware:**
- Venus vibrator device
- Cachito physical controller — already paired with the Venus device
- Mac with Bluetooth

**Software:**
- Python 3.12+ with [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- The bridge server: **[github.com/AmandaClarke61/toybridge](https://github.com/AmandaClarke61/toybridge)**

---

## Setup (one time)

### Step 1 — Get the code

```bash
git clone https://github.com/AmandaClarke61/toybridge venus-ble
cd venus-ble
uv sync
```

### Step 2 — Find your DEVICE_ID

This is the most important step. Every Cachito controller has a unique 4-hex pairing ID. You need to capture yours.

1. Open Cachito app on your iPhone and connect it to Venus
2. On your Mac, run:

```bash
uv run 3-control/sniff_cachito.py
```

3. In the Cachito app, tap any vibration button
4. The terminal will print something like:

```
[SERVICE UUID CMD] 7100-01-cc-8200-cbc5-040a-640000...
  #### (device_id): cbc5  ← SAVE THIS!
```

5. Copy the 4-character `device_id` value (e.g. `cbc5`)

### Step 3 — Set your DEVICE_ID

Open `4-bridge/ble_worker.py` and edit line 14:

```python
DEVICE_ID = "cbc5"   # ← replace with your value from Step 2
```

### Step 4 — Grant Bluetooth permission

macOS requires explicit Bluetooth access. On first run it will prompt you — click Allow.

### Step 5 — Start the server

> The server binds to `localhost` only and makes no external network requests. You can review the full source at [server.py](https://github.com/AmandaClarke61/toybridge/blob/main/4-bridge/server.py) and [ble_worker.py](https://github.com/AmandaClarke61/toybridge/blob/main/4-bridge/ble_worker.py) before running.

```bash
uv run 4-bridge/server.py
```

You should see:
```
Initializing BLE worker (~5s)...
[BLE Worker] Ready
MCP server running on port 8888...
```

Leave this terminal open. The server runs on **port 8888**.

---

## OpenClaw integration

If OpenClaw runs in **Docker** (standard setup), the host machine is reachable at `host.docker.internal`.

If OpenClaw runs **natively** (not in Docker), use `localhost` instead.

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

---

## Intensity guide

| Range  | Feel               |
|--------|--------------------|
| 1–20   | Gentle             |
| 30–50  | Medium             |
| 60–80  | Strong             |
| 90–100 | Maximum            |

---

## Preset patterns

| Pattern | What it does                               |
|---------|--------------------------------------------|
| `pulse` | Bursts of 80%, 5 times                    |
| `wave`  | Ramp up 20→100%, then back down, ×2       |
| `tease` | 30% → 70% → 100%, escalating, then stop   |

Example: *"Run the wave pattern"* or *"Give me a 30-second tease session"*

---

## Agent rules

- Always stop (intensity 0) after a timed session unless user says to keep going
- Do **not** use the `notify` tool — use `bash` with `curl`
- Replace `host.docker.internal` with `localhost` if OpenClaw is not in Docker

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `BT not ready` error | Check Bluetooth is on, grant permission in System Settings → Privacy |
| curl fails / connection refused | Make sure `server.py` is still running |
| Device doesn't respond | Double-check `DEVICE_ID` in `ble_worker.py` matches your Cachito controller |
| Wrong intensity | Venus accepts 0–100; values outside this range are clamped |
