#!/usr/bin/env python3
"""
解析 Apple PacketLogger (pklg) 文件，提取 BLE GATT Write 命令

pklg 格式：
- 每个包前有 header: timestamp(8) + size(4) + type(1)
- 但 Apple 的 pklg 实际用的是 PacketLogger 格式

我们直接搜索 ATT Write 命令的 opcode 特征
"""

import struct
import sys
from pathlib import Path

PKLG_FILE = "/Users/liuyi/Documents/Projects/claudetotoy/sysdiagnose/sysdiagnose_2026.03.06_02-39-29-0500_iPhone-OS_iPhone_22H124/logs/Bluetooth/bluetoothd-hci-latest.pklg"

# ATT opcodes
ATT_WRITE_REQ = 0x12
ATT_WRITE_CMD = 0x52  # write without response
ATT_READ_RSP = 0x0B
ATT_HANDLE_VALUE_NOTIF = 0x1B

# Known Venus characteristic handles (from our GATT discovery)
# Service 06aa1910
KNOWN_HANDLES = {
    # From connect_venus.py output, the handles were printed
    # We'll extract them from the raw data
}


def parse_pklg(filepath):
    """Parse Apple PacketLogger format"""
    data = Path(filepath).read_bytes()
    pos = 0
    packets = []

    while pos < len(data) - 13:
        # PacketLogger header: 4 bytes length, 8 bytes timestamp, 1 byte type
        try:
            pkt_len = struct.unpack('>I', data[pos:pos+4])[0]
            timestamp = struct.unpack('>Q', data[pos+4:pos+12])[0]
            pkt_type = data[pos+12]

            if pkt_len < 1 or pkt_len > 65535:
                pos += 1
                continue

            header_size = 13  # 4 + 8 + 1
            pkt_data = data[pos+header_size:pos+4+pkt_len]

            if len(pkt_data) > 0:
                packets.append((timestamp, pkt_type, pkt_data))

            pos += 4 + pkt_len
        except:
            pos += 1

    return packets


def find_att_writes(packets):
    """Find ATT Write commands in HCI packets"""
    writes = []
    notifs = []

    for ts, pkt_type, pkt_data in packets:
        # Look for ACL data packets (type 0x02 in HCI)
        # In pklg, we need to search for ATT opcodes within the data
        for i in range(len(pkt_data) - 3):
            byte = pkt_data[i]

            # ATT Write Request (opcode 0x12): handle(2) + value
            if byte == ATT_WRITE_REQ and i + 3 < len(pkt_data):
                handle = struct.unpack('<H', pkt_data[i+1:i+3])[0]
                value = pkt_data[i+3:min(i+23, len(pkt_data))]  # max 20 bytes
                if 0 < handle < 0x100 and len(value) > 0:
                    writes.append(('WRITE_REQ', ts, handle, value))

            # ATT Write Command (opcode 0x52): handle(2) + value
            elif byte == ATT_WRITE_CMD and i + 3 < len(pkt_data):
                handle = struct.unpack('<H', pkt_data[i+1:i+3])[0]
                value = pkt_data[i+3:min(i+23, len(pkt_data))]
                if 0 < handle < 0x100 and len(value) > 0:
                    writes.append(('WRITE_CMD', ts, handle, value))

            # ATT Notification (opcode 0x1B): handle(2) + value
            elif byte == ATT_HANDLE_VALUE_NOTIF and i + 3 < len(pkt_data):
                handle = struct.unpack('<H', pkt_data[i+1:i+3])[0]
                value = pkt_data[i+3:min(i+23, len(pkt_data))]
                if 0 < handle < 0x100 and len(value) > 0:
                    notifs.append(('NOTIFY', ts, handle, value))

    return writes, notifs


def main():
    print("=" * 60)
    print("📦 解析 BLE 抓包文件")
    print("=" * 60)

    print(f"\n📂 文件: {Path(PKLG_FILE).name}")
    print(f"   大小: {Path(PKLG_FILE).stat().st_size:,} bytes")

    print("\n⏳ 解析中...")
    packets = parse_pklg(PKLG_FILE)
    print(f"   找到 {len(packets)} 个数据包")

    print("\n🔍 搜索 ATT Write 命令...")
    writes, notifs = find_att_writes(packets)
    print(f"   GATT Writes: {len(writes)} 个")
    print(f"   Notifications: {len(notifs)} 个")

    if writes:
        print(f"\n{'=' * 60}")
        print("📝 所有 GATT Write 命令")
        print("=" * 60)

        # Group by handle
        handle_groups = {}
        for wtype, ts, handle, value in writes:
            if handle not in handle_groups:
                handle_groups[handle] = []
            handle_groups[handle].append((wtype, ts, value))

        for handle in sorted(handle_groups.keys()):
            items = handle_groups[handle]
            print(f"\n  Handle 0x{handle:04X} ({len(items)} 次写入):")
            for wtype, ts, value in items[:20]:  # 最多20条
                print(f"    [{wtype:9s}] {value.hex(' ')}")
            if len(items) > 20:
                print(f"    ... 还有 {len(items)-20} 条")

    if notifs:
        print(f"\n{'=' * 60}")
        print("📥 Notifications")
        print("=" * 60)

        handle_groups = {}
        for wtype, ts, handle, value in notifs:
            if handle not in handle_groups:
                handle_groups[handle] = []
            handle_groups[handle].append((ts, value))

        for handle in sorted(handle_groups.keys()):
            items = handle_groups[handle]
            print(f"\n  Handle 0x{handle:04X} ({len(items)} 条):")
            for ts, value in items[:10]:
                print(f"    {value.hex(' ')}")
            if len(items) > 10:
                print(f"    ... 还有 {len(items)-10} 条")

    # 也输出原始数据的前几百字节看格式
    print(f"\n{'=' * 60}")
    print("🔬 文件头部（前200字节）:")
    print("=" * 60)
    raw = Path(PKLG_FILE).read_bytes()[:200]
    for i in range(0, len(raw), 16):
        hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
        print(f"  {i:04x}: {hex_part:48s} {ascii_part}")


if __name__ == "__main__":
    main()
