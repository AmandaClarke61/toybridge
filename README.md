# ClaudeToToy

> Control BLE intimate toys with Claude AI or OpenClaw — reverse-engineered Cachito protocol

This project runs a local bridge server on your Mac that translates AI instructions into BLE commands for Cachito-protocol toys (Venus, SK, DX, SK4, etc.).

**Two ways to use it:**

| | Claude (claude.ai) | OpenClaw |
|---|---|---|
| How Claude talks to the server | MCP Custom Connector (cloud) | Skill file + curl (local) |
| Requires | Pro account + Cloudflare Tunnel | OpenClaw install |
| Works remotely? | Yes — from anywhere | Local only |
| Setup complexity | Higher | Lower |

```
──── Option A: Claude ────────────────────────────────────────
claude.ai ──► Cloudflare Tunnel ──► server.py:8888 ──► BLE ──► Toy
                                       (/mcp endpoint)

──── Option B: OpenClaw ──────────────────────────────────────
OpenClaw ─────────────────────────► server.py:8888 ──► BLE ──► Toy
                    (curl → /vibrate, /stop, /status)
```

---

## How It Works

Most people assume BLE toys are controlled via GATT writes (connect → write characteristic → device responds). After reverse-engineering the Cachito Android APK with [jadx](https://github.com/skylot/jadx), I discovered these devices work completely differently:

**The phone broadcasts BLE advertisements. The toy listens passively.**

The command is encoded as a **128-bit Service UUID** in the advertisement packet:

```
71000182-0400-cbc5-040a-3700000000cd
│   │ │  │    │    │    │            │
│   │ │  │    │    │    └─ intensity └─ checksum
│   │ │  │    │    └─ device pairing ID (####)
│   │ │  │    └─ command code
│   │ └──┘ random sequence byte
│   └─ device type (01 for Venus)
└─ protocol header
```

This means no GATT connection, no OS-level pairing — any device that can advertise BLE service UUIDs can send commands.

---

## Supported Devices

Tested with the **Venus (小猫爪)** device. Other Cachito-protocol devices share the same mechanism with different parameters:

| Device | Type byte | Vibrate param1 | Stop param1 |
|--------|-----------|----------------|-------------|
| Venus  | `01`      | `040a`         | `0601`      |
| SK     | `02`      | `0302`         | different   |
| DX     | `03`      | `0100`         | different   |
| SK4    | `17`      | `0100`         | different   |

---

## Part 1 — One-Time Hardware Setup

This section is the same regardless of whether you use Claude or OpenClaw.

### Requirements

- **Mac** with Bluetooth (Windows/Linux not supported — requires macOS CoreBluetooth)
- A **Cachito-protocol BLE toy**
- The **Cachito app** on iPhone or Android (needed once, to capture your device ID)
- [uv](https://docs.astral.sh/uv/) — Python package manager

### Step 1 — Install

```bash
git clone https://github.com/AmandaClarke61/toybridge
cd toybridge
curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv if you don't have it
uv sync
```

### Step 2 — Capture your Device ID

Every Cachito app install generates a random 4-character hex **device pairing ID**. You need to capture it once.

1. Power on your toy
2. Run the sniffer:
   ```bash
   uv run sniff_cachito.py
   ```
3. Open Cachito on your phone and **control the toy** (tap vibrate, change intensity, stop)
4. You'll see output like:
   ```
   [SERVICE UUID CMD] 71000182-0400-cbc5-040a-3700000000cd
     device_type: 0x01
     #### (device_id): cbc5  ← SAVE THIS!
   ```
5. Note the **4-character device ID** (e.g. `cbc5`) and **device type** (e.g. `0x01`)
6. Press `Ctrl+C` to stop

> **Nothing appearing?** Make sure Cachito is actively sending commands (actually tap buttons, don't just open the app). Bluetooth must be on.

> **First run:** macOS will ask for Bluetooth permission — click **Allow**.

### Step 3 — Configure

Edit **both** files and replace `DEVICE_ID` with your captured value:

**`ble_worker.py`** (line 14) and **`control_venus.py`** (line 14):
```python
DEVICE_ID = "cbc5"  # ← replace with your value
```

**Non-Venus device?** Also update the device type and params in `ble_worker.py`:
```python
0x01,        # device type byte — change to match your device (see table above)
0x04, 0x0a,  # vibrate param1 — change to match your device
0x06, 0x01,  # stop param1 — change to match your device
```

### Step 4 — Verify locally

```bash
uv run control_venus.py vibrate 50   # 50% intensity
uv run control_venus.py stop
uv run control_venus.py demo         # ramp up/down demo
```

If the toy responds, hardware setup is complete. Proceed to whichever connection method you want below.

---

## Part 2A — Connect with Claude (claude.ai)

**Requirements:** claude.ai **Pro account** (Custom Connectors are a Pro feature) + internet connection

### Step 1 — Install Cloudflare Tunnel

```bash
brew install cloudflare/cloudflare/cloudflared
```

### Step 2 — Start the server

**Terminal 1 — MCP Server:**
```bash
uv run server.py
```
You should see `[BLE Worker] 就绪`. Keep this running.

**Terminal 2 — Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8888 --protocol http2
```
Note the `https://xxxx.trycloudflare.com` URL in the output.

### Step 3 — Add to claude.ai

1. Go to [claude.ai](https://claude.ai)
2. **Settings → Connectors → Add Custom Connector**
3. URL: `https://xxxx.trycloudflare.com/mcp`
4. Save, then **open a new conversation**

Claude now has access to:
- `vibrate(intensity)` — set vibration 0–100%
- `stop()` — stop immediately
- `pattern(name)` — preset patterns: `pulse`, `wave`, `tease`
- `status()` — check current state

Try: *"Vibrate at 50% for 5 seconds then stop"*

> **Tunnel URL changes on every restart.** When you restart `cloudflared`, go back to Settings → Connectors and update the URL. For a permanent URL, set up a [named tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) with your own domain.

---

## Part 2B — Connect with OpenClaw

**Requirements:** [OpenClaw](https://openclaw.ai) installed on your Mac

The server exposes a local REST API on port 8888. OpenClaw calls it directly via curl — no tunnel needed.

### Step 1 — Start the server

```bash
uv run server.py
```
You should see `[BLE Worker] 就绪`. Keep this running.

### Step 2 — Install the OpenClaw skill

```bash
cp -r clawhub-skill/venus-ble-vibrator ~/.openclaw/skills/
```

Or ask OpenClaw: `install skill venus-ble-vibrator` (if you've published the skill to ClawHub).

### Step 3 — Use it

Open OpenClaw and say things like:
- *"Vibrate at 60%"*
- *"Run the wave pattern for 30 seconds"*
- *"Stop"*

OpenClaw calls the local server at `http://localhost:8888`. If OpenClaw runs in Docker, it uses `http://host.docker.internal:8888` automatically (configured in the skill file).

---

## Troubleshooting

**Toy doesn't respond to `control_venus.py`**
- Check `DEVICE_ID` matches what `sniff_cachito.py` captured (in both `ble_worker.py` and `control_venus.py`)
- Make sure the toy is on and in range

**`sniff_cachito.py` shows nothing**
- Cachito must be actively sending commands — actually tap the vibrate button, don't just open the app
- Check Mac Bluetooth is on; click Allow on the permissions prompt if it appears

**`ERROR: BT not ready`**
- System Settings → Privacy & Security → Bluetooth → enable access for your terminal app
- Make sure Bluetooth is enabled on your Mac

**`uv: command not found`**
- Restart your terminal after installing uv (it adds to `~/.local/bin`)

**Claude: "no tools available"**
- Both `server.py` and `cloudflared` must be running
- Connector URL must end with `/mcp`
- Try removing and re-adding the Connector in claude.ai settings

**OpenClaw: `connection refused`**
- Make sure `server.py` is still running
- Check whether OpenClaw runs in Docker (use `host.docker.internal`) or natively (use `localhost`)

---

## Protocol Reference

```
Byte  0    : 0x71  — protocol header
Byte  1    : 0x00
Byte  2    : 0x01  — device type (0x01 = Venus)
Byte  3    : 0xRR  — random sequence byte (0x64–0xFF)
Bytes 4–5  : 0x04 0x00  — command code
Bytes 6–7  : 0xDD 0xDD  — device pairing ID (####)
Bytes 8–9  : param1 — 0x04 0x0a (vibrate) / 0x06 0x01 (stop)
Byte  10   : 0xII  — intensity (0x00–0x64 = 0–100%)
Bytes 11–14: 0x00 × 4  — padding
Byte  15   : checksum = sum(bytes 0–14) mod 256
```

Checksum example:
```
71 00 01 82 04 00 cb c5 04 0a 37 00 00 00 00
sum = 0x2CD  →  checksum = 0xCD  ✓
```

---

## Architecture Notes

**Why BLE advertising instead of GATT?** Discovered via APK reverse engineering — `BleAdvertiser.java` uses `addServiceUuid()` to broadcast commands. The toy never exposes a writable GATT characteristic for control.

**Why a subprocess for BLE?** CoreBluetooth on macOS requires callbacks on the main thread. Since uvicorn occupies the main thread, `ble_worker.py` runs as a separate process with its own `NSRunLoop`.

**Why Cloudflare Tunnel (for Claude)?** claude.ai Custom Connectors require a public HTTPS endpoint. Cloudflare Tunnel exposes the local server without port forwarding.

---

## Files

| File | Purpose |
|------|---------|
| `sniff_cachito.py` | Capture Cachito BLE commands from your phone |
| `control_venus.py` | CLI tool for direct local control (testing) |
| `ble_worker.py` | BLE advertiser subprocess |
| `server.py` | MCP + REST server (port 8888) |
| `clawhub-skill/venus-ble-vibrator/` | OpenClaw skill |

---

## License

MIT
