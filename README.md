# ToyBridge

> Reverse-engineer any BLE toy's protocol, then control it with AI.

## Do You Even Need This?

**Check first:** Is your device already supported by [Buttplug.io](https://iostindex.com/?filter0BrandName=Lovense,We-Vibe,Satisfyer,Kiiroo,Lelo)?

If yes — **you don't need to reverse-engineer anything.** Use [Intiface Central](https://intiface.com/central/) + [buttplug-mcp](https://github.com/ConAcademy/buttplug-mcp) and you're done. It supports 700+ devices (Lovense, We-Vibe, Satisfyer, Kiiroo, etc.) out of the box, cross-platform. We even have an OpenClaw skill for it: [`4-bridge/clawhub-skill/intiface-control/`](4-bridge/clawhub-skill/intiface-control/).

**This project is for devices that Buttplug.io does NOT support** — obscure brands, China-only toys, devices with proprietary protocols that nobody has cracked yet. Like the Cachito/小猫爪 Venus vibrator we used as our case study.

---

## What This Project Does

1. **A BLE reverse-engineering toolkit** — scripts to discover, scan, explore, and crack the protocol of an unknown BLE device
2. **An AI bridge server** — once you know the protocol, connect the toy to [Claude](https://claude.ai) or [OpenClaw](https://openclaw.ai) so an AI can control it

The whole process is documented using the **Venus (小猫爪/Cachito)** vibrator as a real-world case study.

```
┌─────────────────────────────────────────────────────┐
│                  Your journey                       │
│                                                     │
│  Unknown BLE toy                                    │
│       ↓                                             │
│  1-discover/  →  Find the device in BLE scan        │
│       ↓                                             │
│  2-reverse/   →  Explore GATT, sniff packets,       │
│                  brute-force commands                │
│       ↓                                             │
│  3-control/   →  Crack the protocol, verify locally │
│       ↓                                             │
│  4-bridge/    →  Connect to Claude or OpenClaw       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## The Venus Case Study

Most people assume BLE toys use GATT writes (connect → write to a characteristic → device responds). We tried that first — see `2-reverse/` for every script we used. All GATT approaches failed.

After reverse-engineering the Cachito Android APK with [jadx](https://github.com/skylot/jadx), we discovered something unexpected:

**The phone broadcasts BLE advertisements. The toy passively listens.**

The command is encoded as a 128-bit Service UUID:

```
71000182-0400-cbc5-040a-3700000000cd
│   │ │  │    │    │    │            │
│   │ │  │    │    │    └─ intensity └─ checksum
│   │ │  │    │    └─ device pairing ID
│   │ │  │    └─ command code
│   │ └──┘ random sequence byte
│   └─ device type
└─ protocol header
```

No GATT connection. No OS-level pairing. Any device that can broadcast BLE service UUIDs can send commands.

Full protocol docs: [`docs/protocol.md`](docs/protocol.md)

---

## Step 1 — Discover Your Device

> *"I have a BLE toy. Which device is it in the scan?"*

```bash
uv run 1-discover/realtime_scan.py    # watch devices appear in real-time
uv run 1-discover/scan_device.py      # compare scan with toy ON vs OFF
uv run 1-discover/auto_explore.py     # auto-connect strongest signals, look for writable characteristics
```

| Script | What it does |
|--------|-------------|
| `realtime_scan.py` | Real-time BLE listener — turn on your toy and see what appears |
| `scan_device.py` | Differential scan — scans with toy ON, then OFF, shows which devices disappeared |
| `auto_explore.py` | Connects to top 10 by signal strength, lists GATT services and writable characteristics |

---

## Step 2 — Reverse-Engineer the Protocol

> *"I found the device. How do I control it?"*

```bash
uv run 2-reverse/connect_venus.py     # connect and dump full GATT service tree
uv run 2-reverse/explore_venus.py     # explore + write test on every writable characteristic
uv run 2-reverse/hold_venus.py        # occupy BLE connection to verify device identity
uv run 2-reverse/bruteforce_test.py   # try common BLE command formats (single byte, Lovense, IoT, ...)
uv run 2-reverse/replay_test.py       # replay captured auth tokens + control commands
uv run 2-reverse/test_auth.py         # attempt to unlock write-protected characteristics
uv run 2-reverse/parse_pklg.py        # parse Apple sysdiagnose BLE packet capture (.pklg)
uv run 2-reverse/analyze_protocol.py  # extract and analyze command sequences from capture
```

| Script | What it does |
|--------|-------------|
| `connect_venus.py` | Connect to known device, list all GATT services/characteristics with values |
| `explore_venus.py` | Venus-specific explorer — tries writing 0x01 to every writable characteristic |
| `hold_venus.py` | Occupy the BLE connection — if Cachito can't connect while Mac is holding, it's your toy |
| `bruteforce_test.py` | Try dozens of common BLE command formats (single byte, ASCII, IoT headers, etc.) |
| `replay_test.py` | Replay auth tokens and control commands captured from HCI packet log |
| `test_auth.py` | Try to unlock write-protected characteristics by writing auth tokens first |
| `parse_pklg.py` | Parse Apple PacketLogger (.pklg) files from sysdiagnose to extract ATT writes |
| `analyze_protocol.py` | Detailed analysis of all ATT events — group by handle, find patterns |

For Venus, all GATT approaches failed → led to APK reverse-engineering → discovered the BLE advertising protocol.

---

## Step 3 — Verify Locally

> *"I cracked the protocol. Let me test it."*

For Cachito-protocol devices:

### Capture your Device ID

```bash
uv run 3-control/sniff_cachito.py
```

Open the Cachito app on your phone and tap vibrate. The sniffer captures the command UUID and extracts the 4-character device pairing ID (e.g. `cbc5`).

### Configure

Edit `4-bridge/ble_worker.py` line 14:
```python
DEVICE_ID = "cbc5"  # ← your value
```

Also edit `3-control/control_venus.py` line 14 with the same value.

### Test

```bash
uv run 3-control/control_venus.py vibrate 50   # 50% intensity
uv run 3-control/control_venus.py stop
uv run 3-control/control_venus.py demo         # ramp up/down
```

If the toy responds, you're ready for AI control.

---

## Step 4 — Connect to AI

> *"It works. Now let an AI control it."*

### Option A: Claude (claude.ai)

```
claude.ai → Cloudflare Tunnel → server.py:8888 → BLE → Toy
```

**Requirements:** Claude Pro account + [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

**Terminal 1 — Start the server:**
```bash
uv run 4-bridge/server.py
```

**Terminal 2 — Start the tunnel:**
```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared tunnel --url http://localhost:8888 --protocol http2
```

Note the `https://xxxx.trycloudflare.com` URL.

**Connect Claude:**
1. Go to [claude.ai](https://claude.ai) → Settings → Connectors → Add Custom Connector
2. URL: `https://xxxx.trycloudflare.com/mcp`
3. Open a new conversation

Claude now has: `vibrate(intensity)`, `stop()`, `pattern(name)`, `status()`

Try: *"Vibrate at 50% for 5 seconds then stop"*

> Tunnel URL changes on every restart. For a permanent URL, set up a [named tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) with your own domain.

### Option B: OpenClaw

```
OpenClaw → curl → server.py:8888 → BLE → Toy
```

**Requirements:** [OpenClaw](https://openclaw.ai) installed on your Mac

**Start the server:**
```bash
uv run 4-bridge/server.py
```

**Install the skill:**
```bash
cp -r 4-bridge/clawhub-skill/venus-ble-vibrator ~/.openclaw/skills/
```

Or ask OpenClaw: `install skill venus-ble-vibrator`

Then just talk to OpenClaw: *"Vibrate at 60%"*, *"Run the wave pattern"*, *"Stop"*

---

## Requirements

- **macOS** with Bluetooth (CoreBluetooth required — no Windows/Linux support)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Python 3.12+
- A BLE toy to reverse-engineer

```bash
git clone https://github.com/AmandaClarke61/toybridge
cd toybridge
curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv if needed
uv sync
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `uv: command not found` | Restart terminal after installing uv |
| `ERROR: BT not ready` | System Settings → Privacy → Bluetooth → allow your terminal |
| `sniff_cachito.py` shows nothing | Cachito must be actively sending — tap vibrate buttons, don't just open the app |
| Toy doesn't respond to `control_venus.py` | Check DEVICE_ID matches in both `ble_worker.py` and `control_venus.py` |
| Claude: "no tools available" | Both `server.py` and `cloudflared` must be running; URL must end with `/mcp` |
| OpenClaw: `connection refused` | Make sure `server.py` is running; Docker uses `host.docker.internal`, native uses `localhost` |

---

## Project Structure

```
toybridge/
├── 1-discover/              # Find your device in BLE scan
│   ├── realtime_scan.py     # Real-time BLE listener
│   ├── scan_device.py       # Differential scan (on vs off)
│   └── auto_explore.py      # Auto-connect and explore top signals
├── 2-reverse/               # Reverse-engineer the protocol
│   ├── connect_venus.py     # Connect and dump GATT services
│   ├── explore_venus.py     # Explore + write test all characteristics
│   ├── hold_venus.py        # Occupy connection to verify identity
│   ├── bruteforce_test.py   # Brute-force common command formats
│   ├── replay_test.py       # Replay captured auth + control sequences
│   ├── test_auth.py         # Try auth token unlock
│   ├── parse_pklg.py        # Parse Apple BLE packet captures
│   └── analyze_protocol.py  # Analyze captured command patterns
├── 3-control/               # Local control (after cracking protocol)
│   ├── sniff_cachito.py     # Capture Cachito commands to get device ID
│   └── control_venus.py     # CLI: vibrate, stop, demo
├── 4-bridge/                # AI integration
│   ├── server.py            # MCP + REST server (port 8888)
│   ├── ble_worker.py        # BLE advertiser subprocess
│   └── clawhub-skill/       # OpenClaw skills
│       ├── toybridge/           # Generic — any device you've reverse-engineered
│       ├── venus-ble-vibrator/  # Venus/Cachito specific
│       └── intiface-control/    # Buttplug.io devices (no RE needed)
└── docs/
    └── protocol.md          # Full Cachito protocol documentation
```

---

## License

MIT
