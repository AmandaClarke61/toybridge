#!/usr/bin/env python3
"""
BLE 实时监听器 — 实时显示每个新出现的设备

使用方法：
1. 先彻底关掉手机上的 Cachito App（从后台划掉！）
2. 运行此脚本
3. 然后【关掉小猫爪再重新开机】
4. 观察哪个设备是新出现的
"""

import asyncio
from datetime import datetime
from bleak import BleakScanner


async def main():
    seen = set()
    toy_keywords = ["venus", "ply", "toy", "cat", "kis", "cach", "meng", "moe", "paw", "claw"]

    print("=" * 60)
    print("👁️  BLE 实时监听器")
    print("=" * 60)
    print()
    print("⚠️  请先做以下操作：")
    print("   1. iPhone 上 Cachito App 从后台彻底划掉")
    print("   2. 小猫爪先【关机】")
    print()
    input("准备好后按回车开始监听...")
    print()
    print("🔍 正在监听... 现在请【打开小猫爪电源】")
    print("   每个新出现的设备会实时显示")
    print("   按 Ctrl+C 停止")
    print("─" * 60)

    def callback(device, adv_data):
        if device.address in seen:
            return
        seen.add(device.address)

        now = datetime.now().strftime("%H:%M:%S")
        name = device.name or adv_data.local_name or "(未知)"
        rssi = adv_data.rssi
        svc_count = len(adv_data.service_uuids) if adv_data.service_uuids else 0
        mfr_data = adv_data.manufacturer_data

        # 检查是否有可疑关键词
        is_suspect = any(kw in name.lower() for kw in toy_keywords)
        flag = " 🎯 ← 可能是你的设备！" if is_suspect else ""

        print(f"  [{now}] {name:30s} | {rssi:4d} dBm | 服务:{svc_count} | {device.address}{flag}")

        # 如果有厂商数据，也打印出来
        if mfr_data:
            for mfr_id, data in mfr_data.items():
                print(f"           厂商ID: 0x{mfr_id:04X} | 数据: {data.hex(' ')}")

        # 如果有广播的服务UUID，打印
        if adv_data.service_uuids:
            for svc_uuid in adv_data.service_uuids:
                print(f"           服务UUID: {svc_uuid}")

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()

    try:
        # 监听60秒
        for i in range(60):
            await asyncio.sleep(1)
            if i == 10:
                print("─" * 60)
                print("  💡 如果还没看到可疑设备，确认小猫爪已开机")
                print("─" * 60)
            if i == 30:
                print("─" * 60)
                print(f"  📊 已发现 {len(seen)} 个设备，继续监听30秒...")
                print("─" * 60)
    except KeyboardInterrupt:
        pass
    finally:
        await scanner.stop()

    print()
    print(f"✅ 监听结束，共发现 {len(seen)} 个设备")


if __name__ == "__main__":
    asyncio.run(main())
