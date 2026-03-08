#!/usr/bin/env python3
"""
从抓包数据中提取完整的命令序列，然后重放到 Venus 设备上

关键发现：
- Handle 0x0019: 认证数据 (20字节加密)
- Handle 0x0033: 控制命令 (4字节: 00 00 00 XX)
- Handle 0x0002: 状态/配置 (2字节)
"""

import struct
from pathlib import Path

PKLG_FILE = "/Users/liuyi/Documents/Projects/claudetotoy/sysdiagnose/sysdiagnose_2026.03.06_02-39-29-0500_iPhone-OS_iPhone_22H124/logs/Bluetooth/bluetoothd-hci-latest.pklg"

ATT_WRITE_REQ = 0x12
ATT_WRITE_CMD = 0x52
ATT_HANDLE_VALUE_NOTIF = 0x1B


def parse_pklg(filepath):
    data = Path(filepath).read_bytes()
    pos = 0
    packets = []
    while pos < len(data) - 13:
        try:
            pkt_len = struct.unpack('>I', data[pos:pos+4])[0]
            timestamp = struct.unpack('>Q', data[pos+4:pos+12])[0]
            pkt_type = data[pos+12]
            if pkt_len < 1 or pkt_len > 65535:
                pos += 1
                continue
            pkt_data = data[pos+13:pos+4+pkt_len]
            if len(pkt_data) > 0:
                packets.append((timestamp, pkt_type, pkt_data))
            pos += 4 + pkt_len
        except:
            pos += 1
    return packets


def extract_all_writes(packets):
    """提取所有写命令，按时间排序"""
    events = []
    for ts, pkt_type, pkt_data in packets:
        for i in range(len(pkt_data) - 3):
            byte = pkt_data[i]
            if byte in (ATT_WRITE_REQ, ATT_WRITE_CMD):
                handle = struct.unpack('<H', pkt_data[i+1:i+3])[0]
                value = pkt_data[i+3:min(i+23, len(pkt_data))]
                if 0 < handle < 0x200 and len(value) > 0:
                    wtype = 'REQ' if byte == ATT_WRITE_REQ else 'CMD'
                    events.append((ts, wtype, handle, value))
            elif byte == ATT_HANDLE_VALUE_NOTIF:
                handle = struct.unpack('<H', pkt_data[i+1:i+3])[0]
                value = pkt_data[i+3:min(i+23, len(pkt_data))]
                if 0 < handle < 0x200 and len(value) > 0:
                    events.append((ts, 'NOTIF', handle, value))
    return sorted(events, key=lambda x: x[0])


def main():
    print("=" * 70)
    print("🔬 详细协议分析")
    print("=" * 70)

    packets = parse_pklg(PKLG_FILE)
    events = extract_all_writes(packets)

    print(f"\n总事件数: {len(events)}")

    # 打印前100个事件（按时间顺序）
    print(f"\n{'=' * 70}")
    print("📜 前 100 个事件（时间序）— 这是连接+认证+控制的完整流程")
    print("=" * 70)

    for i, (ts, etype, handle, value) in enumerate(events[:100]):
        direction = "→" if etype in ('REQ', 'CMD') else "←"
        print(f"  [{i:3d}] {direction} {etype:5s} H=0x{handle:04X} | {value.hex(' ')}")

    # Handle 0x0033 详细分析
    h33_writes = [(ts, v) for ts, t, h, v in events if h == 0x0033 and t in ('REQ', 'CMD')]
    if h33_writes:
        print(f"\n{'=' * 70}")
        print(f"📊 Handle 0x0033 控制命令详细分析 ({len(h33_writes)} 条)")
        print("=" * 70)

        values = set()
        for ts, v in h33_writes:
            values.add(v.hex())

        print(f"\n  去重后的命令值 ({len(values)} 种):")
        for v in sorted(values):
            count = sum(1 for _, val in h33_writes if val.hex() == v)
            print(f"    {v}  (出现 {count} 次)")

    # Handle 0x0019 详细分析
    h19_writes = [(ts, v) for ts, t, h, v in events if h == 0x0019 and t in ('REQ', 'CMD')]
    if h19_writes:
        print(f"\n{'=' * 70}")
        print(f"🔐 Handle 0x0019 认证数据 ({len(h19_writes)} 条)")
        print("=" * 70)

        values = set()
        for ts, v in h19_writes:
            values.add(v.hex())

        print(f"\n  去重后 ({len(values)} 种):")
        for v in sorted(values):
            count = sum(1 for _, val in h19_writes if val.hex() == v)
            print(f"    {v}  (出现 {count} 次)")

    # Handle 0x0002 详细分析
    h02_writes = [(ts, v) for ts, t, h, v in events if h == 0x0002 and t in ('REQ', 'CMD')]
    if h02_writes:
        print(f"\n{'=' * 70}")
        print(f"📡 Handle 0x0002 数据 ({len(h02_writes)} 条)")
        print("=" * 70)

        values = set()
        for ts, v in h02_writes:
            values.add(v.hex())

        print(f"\n  去重后 ({len(values)} 种):")
        for v in sorted(values):
            count = sum(1 for _, val in h02_writes if val.hex() == v)
            print(f"    {v}  (出现 {count} 次)")


if __name__ == "__main__":
    main()
