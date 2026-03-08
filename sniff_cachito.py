#!/usr/bin/env python3
"""
Sniff BLE advertisements sent by Cachito app when controlling Venus.
Run this on Mac while using Cachito on iPhone to control the toy.
This will capture the command format including the real #### value.
"""
import asyncio
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

seen_commands = set()

def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    # Look for service UUIDs starting with "7100"
    for uuid in advertisement_data.service_uuids:
        uuid_clean = uuid.lower().replace("-", "")
        if uuid_clean.startswith("7100"):
            if uuid not in seen_commands:
                seen_commands.add(uuid)
                print(f"\n[SERVICE UUID CMD] {uuid}")
                print(f"  Device: {device.name or '?'} ({device.address})")
                parse_uuid_command(uuid)

    # Look for manufacturer data with company ID 0x71 (113)
    for company_id, data in advertisement_data.manufacturer_data.items():
        if company_id == 0x0071:
            hex_data = data.hex()
            key = f"mfr_{hex_data}"
            if key not in seen_commands:
                seen_commands.add(key)
                print(f"\n[MANUFACTURER DATA 0x71] company_id=0x{company_id:04x}")
                print(f"  Device: {device.name or '?'} ({device.address})")
                print(f"  Data: {hex_data}")
                full = "7100" + hex_data
                print(f"  Full: {full}")

    # Also show manufacturer data from Venus itself (0x2502)
    for company_id, data in advertisement_data.manufacturer_data.items():
        if company_id == 0x2502:
            hex_data = data.hex()
            key = f"venus_{hex_data}"
            if key not in seen_commands:
                seen_commands.add(key)
                print(f"\n[VENUS ADV 0x2502] raw data: {hex_data}")
                print(f"  Device: {device.name or '?'} ({device.address})")


def parse_uuid_command(uuid: str):
    """Parse a 7100xxxx UUID command and extract fields."""
    # Format: 710001RR-0400-DDDD-PPPP-II0000000000CS
    # Field:  hdr+type+rnd  cmd  ####  param1  intensity  padding  checksum
    parts = uuid.split("-")
    if len(parts) != 5:
        print(f"  (unexpected format: {len(parts)} parts)")
        return

    p1, p2, p3, p4, p5 = parts
    # p1 = 710003CC → device_type=03, random=CC
    device_type = p1[4:6]
    random_sn = p1[6:8]
    cmd_code = p2
    device_id = p3  # This is ####
    param1 = p4
    param2 = p5

    print(f"  device_type: 0x{device_type}  ({int(device_type, 16)})")
    print(f"  random_sn:   0x{random_sn}")
    print(f"  cmd_code:    0x{cmd_code}")
    print(f"  #### (device_id): {device_id}  ← SAVE THIS!")
    print(f"  param1:      0x{param1}")
    print(f"  param2:      0x{param2}")


async def main():
    print("Sniffing BLE advertisements for Cachito commands...")
    print("Now use Cachito on iPhone to control Venus.")
    print("Press Ctrl+C to stop.\n")

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    await scanner.stop()
    print(f"\nCaptured {len(seen_commands)} unique commands/events.")


if __name__ == "__main__":
    asyncio.run(main())
