#!/usr/bin/env python3
"""
BLE 批量探索器 — 自动连接信号最强的设备，寻找玩具

使用方法：
1. 打开小猫爪电源
2. 确保 Cachito App 已关闭
3. 运行: python3 -m uv run auto_explore.py
"""

import asyncio
from bleak import BleakScanner, BleakClient


async def scan_with_rssi(timeout=10.0):
    """扫描并返回按信号强度排序的设备列表"""
    found = {}

    def callback(device, adv_data):
        found[device.address] = (
            device.name or adv_data.local_name,
            adv_data.rssi,
            adv_data.service_uuids or [],
            device,
        )

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return found


async def try_explore(device, idx):
    """尝试连接并探索一个设备的 GATT 服务"""
    name = device.name or "(未知)"
    print(f"\n{'─' * 50}")
    print(f"[{idx}] 🔗 尝试连接: {name} ({device.address})")

    try:
        async with BleakClient(device.address, timeout=8.0) as client:
            if not client.is_connected:
                print(f"    ❌ 连接失败")
                return False

            services = client.services
            has_custom = False

            for service in services:
                uuid_short = service.uuid.split('-')[0]
                # 标准蓝牙服务以 0000xxxx 开头，自定义服务通常不同
                is_standard = uuid_short.startswith("0000") and len(uuid_short) == 8
                
                writable_chars = [
                    c for c in service.characteristics
                    if "write" in c.properties or "write-without-response" in c.properties
                ]

                if writable_chars:
                    has_custom = True
                    marker = "⭐" if not is_standard else "  "
                    print(f"    {marker} Service: {service.uuid}")
                    print(f"       描述: {service.description or 'Custom'}")
                    for char in service.characteristics:
                        props = ", ".join(char.properties)
                        print(f"       📌 {char.uuid} [{props}]")
                        if "read" in char.properties:
                            try:
                                val = await client.read_gatt_char(char.uuid)
                                print(f"          值: {val.hex(' ')}")
                            except:
                                pass

            if has_custom:
                print(f"    ✅ 有可写特征，可能是玩具！")
                return True
            else:
                print(f"    ⬜ 没有可写的自定义特征")
                return False

    except asyncio.TimeoutError:
        print(f"    ⏳ 连接超时")
        return False
    except Exception as e:
        print(f"    ❌ 错误: {e}")
        return False


async def main():
    print("=" * 60)
    print("🔍 自动探索器 — 寻找你的小猫爪")
    print("   请确保设备已开机，Cachito App 已关闭")
    print("=" * 60)

    input("\n准备好后按回车开始... ")

    print("\n🔍 扫描中... (10秒)")
    devices = await scan_with_rssi(10.0)

    # 按信号强度排序
    sorted_devices = sorted(
        devices.values(),
        key=lambda x: x[1] if x[1] else -999,
        reverse=True,
    )

    # 取信号最强的前10个
    top = sorted_devices[:10]

    print(f"\n📊 按信号强度排序的前 10 个设备：")
    for i, (name, rssi, svc_uuids, dev) in enumerate(top):
        display = name or "(未知)"
        print(f"  [{i}] {display:20s} | {rssi:4d} dBm | 广播服务: {len(svc_uuids)}")

    print(f"\n🔗 开始逐个连接探索...\n")

    candidates = []
    for i, (name, rssi, svc_uuids, dev) in enumerate(top):
        result = await try_explore(dev, i)
        if result:
            candidates.append((name, rssi, dev))

    print("\n" + "=" * 60)
    if candidates:
        print(f"🎯 找到 {len(candidates)} 个可能的玩具设备：")
        for name, rssi, dev in candidates:
            display = name or "(未知)"
            print(f"   • {display} | {rssi} dBm | {dev.address}")
        print("\n请把以上输出全部复制发给我！")
    else:
        print("😢 前10个设备中没找到疑似玩具。")
        print("   试试以下办法：")
        print("   1. 把设备靠近 Mac 电脑")
        print("   2. 确认 Cachito App 彻底关闭（不只是切到后台）")
        print("   3. 重启设备后再试")


if __name__ == "__main__":
    asyncio.run(main())
