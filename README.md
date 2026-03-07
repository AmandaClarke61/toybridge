# ClaudeToToy

> Control BLE intimate toys with Claude AI via MCP — reverse-engineered Cachito protocol

Ask Claude to control your toy directly from [claude.ai](https://claude.ai) (desktop or mobile). No dedicated app required during use.

```
claude.ai ──► Cloudflare Tunnel ──► MCP Server (Mac) ──► BLE Advertising ──► Toy
```

---

## How It Works

Most people assume BLE toys are controlled via **GATT writes** (connect → write characteristic → device responds). After reverse-engineering the Cachito Android APK with [jadx](https://github.com/skylot/jadx), I discovered these devices work completely differently:

**The phone broadcasts BLE advertisements. The toy listens passively.**

The command is encoded as a **128-bit Service UUID** in the advertisement packet:

```
71000182-0400-cbc5-040a-3700000000cd
│   │ │  │    │    │    │            │
│   │ │  │    │    │    └─ intensity └─ checksum
│   │ │  │    │    └─ device pairing ID (####)
│   │ │  │    └─ command code (0400=vibrate)
│   │ └──┘ random sequence byte
│   └─ device type (01 for Venus)
└─ protocol header
```

This means:
- No GATT connection needed
- The toy never needs to "pair" at the OS level
- Any device that can advertise BLE service UUIDs can send commands

---

## Supported Devices

Tested with the **Venus (小猫爪)** device (type `0x01`). Other Cachito-protocol devices use the same mechanism with different type bytes:

| Device | Type byte | Vibrate param1 | Stop param1 |
|--------|-----------|----------------|-------------|
| Venus  | `01`      | `040a`         | `0601`      |
| SK     | `02`      | `0302`         | different   |
| DX     | `03`      | `0100`         | different   |
| SK4    | `17`      | `0100`         | different   |

To support a different device, run `sniff_cachito.py` while using the Cachito app — it captures the exact command format for your device automatically.

---

## Requirements

- **Mac** with Bluetooth (uses CoreBluetooth for BLE advertising)
- A **Cachito-protocol BLE toy** (Venus, SK, DX, SK4, MB, etc.)
- The **Cachito app** on iPhone/Android (only needed once, to sniff your device ID)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) — Cloudflare Tunnel

---

## Setup

### Step 1 — Install dependencies

```bash
git clone https://github.com/yourusername/ClaudeToToy
cd ClaudeToToy
brew install cloudflare/cloudflare/cloudflared
curl -LsSf https://astral.sh/uv/install.sh | sh
uv add pyobjc-framework-CoreBluetooth mcp
```

### Step 2 — Find your Device ID

Every Cachito app install generates a random 4-character hex **device pairing ID** stored on the toy. Capture it once:

1. Power on your toy
2. Run the sniffer on Mac:
   ```bash
   python3 sniff_cachito.py
   ```
3. Open Cachito on your phone and control the toy (start, change intensity, stop)
4. You'll see output like:
   ```
   [SERVICE UUID CMD] 71000182-0400-cbc5-040a-3700000000cd
     device_type: 0x01
     #### (device_id): cbc5  ← SAVE THIS!
   ```
5. Note the 4-character device ID and your device type

### Step 3 — Configure

Edit `ble_worker.py` and `control_venus.py`, set your captured values:

```python
DEVICE_ID = "cbc5"  # ← replace with your captured value
```

### Step 4 — Test local control

```bash
python3 control_venus.py vibrate 50   # 50% intensity
python3 control_venus.py stop
python3 control_venus.py demo         # ramp up/down demo
```

If the toy responds, you're ready to connect Claude.

### Step 5 — Start the MCP server

**Terminal 1 — MCP Server:**
```bash
uv run server.py
```
You should see `[BLE Worker] ready`.

**Terminal 2 — Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8888 --protocol http2
```
Note the `https://xxxx.trycloudflare.com` URL.

### Step 6 — Connect to claude.ai

1. Go to [claude.ai](https://claude.ai)
2. **Settings → Connectors → Add Custom Connector**
3. URL: `https://xxxx.trycloudflare.com/mcp`
4. Save, then **open a new conversation**

Claude now has these tools:
- `vibrate(intensity)` — set vibration 0–100%
- `stop()` — stop immediately
- `pattern(name)` — preset patterns: `pulse`, `wave`, `tease`
- `status()` — check current state

> **Note:** The Cloudflare Tunnel URL changes on every restart. For a permanent URL, set up a [named tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) with your own domain.

---

## Protocol Reference

### Command UUID format (16 bytes)

```
Byte  0    : 0x71  — protocol header
Byte  1    : 0x00
Byte  2    : 0x01  — device type (0x01 = Venus)
Byte  3    : 0xRR  — random sequence byte (0x64–0xFF)
Bytes 4–5  : 0x04 0x00  — command code (vibrate)
Bytes 6–7  : 0xDD 0xDD  — device pairing ID (####)
Bytes 8–9  : param1 — 0x04 0x0a (vibrate) / 0x06 0x01 (stop)
Byte  10   : 0xII  — intensity (0x00–0x64 = 0–100%)
Bytes 11–14: 0x00 × 4  — padding
Byte  15   : checksum = sum(bytes 0–14) mod 256
```

Formatted as UUID: `BBBBBBBB-CCCC-DDDD-PPPP-IIIIIIIIIICS`

### Checksum example

```
71 00 01 82 04 00 cb c5 04 0a 37 00 00 00 00
sum = 0x2CD  →  checksum = 0xCD  ✓
```

---

## Architecture Notes

### Why BLE advertising instead of GATT?

Discovered via APK reverse engineering — `BleAdvertiser.java` and `BLEHelper.java` in the Cachito source both use `addServiceUuid()` to broadcast commands. The toy never exposes a writable GATT characteristic for control.

### Why a subprocess for BLE?

CoreBluetooth on macOS requires callbacks to be delivered on the main thread (when initialized with `queue: nil`). Since uvicorn's asyncio event loop occupies the main thread, CoreBluetooth state callbacks never fire. The fix: run `ble_worker.py` as a separate process where the main thread is free to pump `NSRunLoop`.

### Why Cloudflare Tunnel?

claude.ai's Custom Connectors require a public HTTPS endpoint. Cloudflare Tunnel exposes the local MCP server without port forwarding or a static IP.

---

## Reversing the Protocol

1. Downloaded Cachito APK from apkpure.com
2. Decompiled with `jadx -d cachito_src cachito.apk`
3. Found `BleAdvertiser.java` → commands go via BLE advertising, not GATT
4. Traced `CommandExtKt.java` → UUID command format with `####` placeholder
5. Found `DataExtKt.getControlDeviceId()` → `####` is a random 4-hex ID per app install
6. Confirmed `BLEHelper.java` uses `builder.addServiceUuid()` → command is the Service UUID itself
7. Built `sniff_cachito.py` to capture real commands from the iPhone passively

---

## Files

| File | Purpose |
|------|---------|
| `sniff_cachito.py` | Capture Cachito BLE commands from your phone |
| `control_venus.py` | CLI tool for direct local control (testing) |
| `ble_worker.py` | BLE advertiser subprocess — NSRunLoop on main thread |
| `server.py` | MCP server (streamable-http, port 8888) |

---

## License

MIT
