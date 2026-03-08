# Cachito BLE Protocol

## Overview

Cachito-protocol devices (Venus, SK, DX, SK4, etc.) are **not** controlled via GATT writes. Instead, the controller broadcasts **BLE advertisements** containing a 128-bit Service UUID that encodes the command. The toy passively listens for these advertisements — no connection, no pairing required.

This was discovered by reverse-engineering the Cachito Android APK with [jadx](https://github.com/skylot/jadx), after exhaustive testing of GATT-based approaches all failed.

## Command Format

Commands are encoded as a 128-bit UUID in a BLE advertisement packet:

```
71000182-0400-cbc5-040a-3700000000cd
│   │ │  │    │    │    │            │
│   │ │  │    │    │    └─ intensity └─ checksum
│   │ │  │    │    └─ device pairing ID
│   │ │  │    └─ command code
│   │ └──┘ random sequence byte
│   └─ device type (01 for Venus)
└─ protocol header
```

### Byte layout

```
Byte  0    : 0x71  — protocol header
Byte  1    : 0x00
Byte  2    : 0x01  — device type (see table below)
Byte  3    : 0xRR  — random sequence byte (0x64–0xFF)
Bytes 4–5  : 0x04 0x00  — command code
Bytes 6–7  : 0xDD 0xDD  — device pairing ID
Bytes 8–9  : param1 — command-specific (see table below)
Byte  10   : 0xII  — intensity (0x00–0x64 = 0–100%)
Bytes 11–14: 0x00 × 4  — padding
Byte  15   : checksum = sum(bytes 0–14) mod 256
```

### Vibrate command

param1 = device-specific vibrate code, intensity = 0x00–0x64

### Stop command

param1 = device-specific stop code, intensity = 0x02

### Checksum example

```
71 00 01 82 04 00 cb c5 04 0a 37 00 00 00 00
sum = 0x2CD  →  checksum = 0xCD  ✓
```

## Supported Devices

| Device | Type byte | Vibrate param1 | Stop param1 |
|--------|-----------|----------------|-------------|
| Venus  | `01`      | `040a`         | `0601`      |
| SK     | `02`      | `0302`         | different   |
| DX     | `03`      | `0100`         | different   |
| SK4    | `17`      | `0100`         | different   |

## Device Pairing ID

Each Cachito app install generates a random 4-character hex pairing ID (e.g. `cbc5`). The toy learns this ID during initial pairing with the physical controller. To control the toy, you must know this ID.

Capture it by sniffing BLE advertisements while the Cachito app sends commands — see `3-control/sniff_cachito.py`.

## Why Not GATT?

The Venus device does expose GATT services with writable characteristics, but:

1. Most writable characteristics return "Writing is not permitted" without prior authentication
2. Authentication requires 20-byte encrypted tokens that change per session
3. Even after replaying captured auth tokens, control commands had no effect

The APK source (`BleAdvertiser.java`) confirmed: the app uses `addServiceUuid()` to broadcast commands as advertisements. The toy never processes incoming GATT writes for motor control.

See `2-reverse/` for the complete exploration scripts that document this dead end.
