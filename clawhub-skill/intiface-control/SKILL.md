---
name: intiface-control
description: Control 750+ BLE intimate devices (Lovense, Kiiroo, We-Vibe, Satisfyer, etc.) from natural language via Intiface Central and buttplug-mcp. Works on macOS, Windows, and Linux. No protocol reverse-engineering required.
metadata: {"openclaw": {"requires": {"bins": ["mcporter", "buttplug-mcp"]}}}
---

# Universal Intimate Device Control via Intiface

Control any [Buttplug.io-compatible device](https://iostindex.com) — 750+ toys across all major brands — using natural language through OpenClaw.

## How it works

```
OpenClaw agent
    → mcporter (stdio)
    → buttplug-mcp
    → Intiface Central (WebSocket)
    → Your device (Bluetooth / USB)
```

No reverse-engineering, no device-specific code. Works on **macOS, Windows, and Linux**.

---

## Prerequisites

- [Intiface Central](https://intiface.com/central/) — free desktop app (cross-platform)
- `buttplug-mcp` — MCP bridge for Buttplug/Intiface
- `mcporter` — installed via OpenClaw's mcporter skill

### Install buttplug-mcp

**macOS (Homebrew):**
```bash
brew tap conacademy/homebrew-tap
brew install conacademy/tap/buttplug-mcp
```

**Other platforms:** Download from [ConAcademy/buttplug-mcp](https://github.com/ConAcademy/buttplug-mcp/releases)

---

## Setup (one time)

### Step 1 — Install and open Intiface Central

Download from [intiface.com/central](https://intiface.com/central/). Open the app and click **Start Server**. Leave it running — it listens on `ws://localhost:12345` by default.

### Step 2 — Connect your device

In Intiface Central, click **Start Scanning**. Power on your toy. Once it appears in the device list, scanning can be stopped.

### Step 3 — Install mcporter skill

Ask OpenClaw: `install skill mcporter`

---

## Commands the agent will use

### List connected devices
```bash
mcporter call --stdio "buttplug-mcp --ws-port 12345" device_vibrate --list
```

### Vibrate a device
```bash
mcporter call --stdio "buttplug-mcp --ws-port 12345" device_vibrate id=0 strength=0.7
```

- `id`: device index (0 = first device)
- `strength`: 0.0 to 1.0 (0.0 = stop)

### Stop
```bash
mcporter call --stdio "buttplug-mcp --ws-port 12345" device_vibrate id=0 strength=0.0
```

---

## Strength guide

| Value | Feel |
|-------|------|
| 0.1–0.2 | Gentle |
| 0.3–0.5 | Medium |
| 0.6–0.8 | Strong |
| 0.9–1.0 | Maximum |

---

## Supported brands (partial list)

Lovense · Kiiroo · We-Vibe · Satisfyer · The Handy · OSR-2/SR-6 · and [700+ more](https://iostindex.com)

---

## Agent rules

- Always stop (strength 0.0) after a timed session unless the user says otherwise
- Use device `id=0` unless the user specifies a different device
- Intiface Central must be running before calling any commands — remind the user if commands fail
- Do not use the `notify` tool

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` | Open Intiface Central and click Start Server |
| Device not found | Click Start Scanning in Intiface Central, power cycle the toy |
| `buttplug-mcp not found` | Run `brew install conacademy/tap/buttplug-mcp` |
| `mcporter not found` | Ask OpenClaw: `install skill mcporter` |
| Wrong device index | List devices first, use the correct `id` |
