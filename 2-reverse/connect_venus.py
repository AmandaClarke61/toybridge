#!/usr/bin/env python3
"""
Venus 精准连接器 — 用已知地址直连小猫爪

使用方法：
1. iPhone 蓝牙关闭
2. 小猫爪开机
3. 运行: python3 -m uv run connect_venus.py
"""

import asyncio
from bleak import BleakScanner, BleakClient

# 已确认的设备信息
DEVICE_ADDRESS = "0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED"
DEVICE_SERVICE = "06aa1910-f22a-11e3-9daa-0002a5d5c51b"


async def main():
    print("=" * 60)
    print("🐱 Venus 小猫爪 精准连接器")
    print(f"   目标地址: {DEVICE_ADDRESS}")
    print("=" * 60)
    print("\n⚠️  请确保 iPhone 蓝牙已关闭，小猫爪已开机")
    input("准备好后按回车... ")

    # 长时间扫描直到找到设备
    print("\n🔍 正在寻找 Venus（最多等 60 秒）...")
    device = None

    def cb(dev, adv):
        nonlocal device
        if dev.address == DEVICE_ADDRESS:
            device = dev
            print(f"   ✅ 找到了！ {dev.name} | {adv.rssi} dBm")

    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()

    for i in range(60):
        if device:
            break
        await asyncio.sleep(1)
        print(f"\r   等待中... {i+1}/60秒", end="", flush=True)

    await scanner.stop()

    if not device:
        print("\n❌ 60秒内未找到设备")
        return

    # 连接并探索
    print(f"\n🔗 连接中...")

    try:
        async with BleakClient(DEVICE_ADDRESS, timeout=20.0) as client:
            if not client.is_connected:
                print("❌ 连接失败")
                return

            print("✅ 已连接！\n")
            print("=" * 60)
            print("📋 GATT 服务列表")
            print("=" * 60)

            writable = []

            for service in client.services:
                print(f"\n🔵 Service: {service.uuid}")
                print(f"   描述: {service.description or 'Custom'}")

                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    is_w = "write" in char.properties or "write-without-response" in char.properties
                    mark = "⭐" if is_w else "  "

                    print(f"   {mark} {char.uuid}  [{props}]")

                    if is_w:
                        writable.append(char)

                    if "read" in char.properties:
                        try:
                            v = await client.read_gatt_char(char.uuid)
                            if v:
                                print(f"      值 (hex): {v.hex(' ')}")
                                t = v.decode('utf-8', errors='ignore').strip('\x00')
                                if t and t.isprintable():
                                    print(f"      值 (text): {t}")
                        except:
                            pass

            print(f"\n{'=' * 60}")
            print(f"📝 可写 Characteristics: {len(writable)} 个")
            print("=" * 60)
            for i, c in enumerate(writable):
                print(f"  [{i}] {c.uuid}  [{', '.join(c.properties)}]")

            # 写入测试
            if writable:
                print(f"\n🧪 写入测试...")
                for i, c in enumerate(writable):
                    try:
                        resp = "write-without-response" not in c.properties
                        await client.write_gatt_char(c.uuid, bytes([0x01]), response=resp)
                        print(f"  [{i}] {c.uuid} ← 0x01 ✅")
                        print(f"       👀 设备有反应吗？等3秒...")
                        await asyncio.sleep(3)

                        await client.write_gatt_char(c.uuid, bytes([0x00]), response=resp)
                        print(f"       ← 0x00 (关)")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"  [{i}] {c.uuid} ← 失败: {e}")

            print(f"\n✅ 完成！请把全部输出发给我。")
            print("   告诉我设备有没有在哪一步振动！")

    except Exception as e:
        print(f"❌ 连接出错: {e}")
        print("   设备可能广播结束了，再试一次")


if __name__ == "__main__":
    asyncio.run(main())
