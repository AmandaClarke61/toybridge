#!/usr/bin/env python3
"""
Venus 连接占用测试 — 验证 Venus 是不是你的小猫爪

Mac 占着 Venus 连接，你用 iPhone Cachito 试控制。
如果 Cachito 还能连 → Venus 不是你的玩具
如果 Cachito 连不上 → Venus 就是
"""

import asyncio
from bleak import BleakScanner, BleakClient

DEVICE_ADDRESS = "0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED"


async def main():
    print("=" * 60)
    print("🔒 Venus 连接占用测试")
    print("=" * 60)
    print("\n⚠️  iPhone 蓝牙先关闭，小猫爪开机")
    input("准备好按回车... ")

    print("\n🔍 寻找 Venus...")
    device = None
    def cb(dev, adv):
        nonlocal device
        if dev.address == DEVICE_ADDRESS:
            device = dev
    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    for i in range(60):
        if device: break
        await asyncio.sleep(1)
        print(f"\r   等待... {i+1}/60s", end="", flush=True)
    await scanner.stop()

    if not device:
        print("\n❌ 未找到 Venus")
        return

    print(f"\n✅ 找到 Venus，连接中...")

    async with BleakClient(DEVICE_ADDRESS, timeout=20.0) as client:
        print("✅ Mac 已占住 Venus 连接！")
        print()
        print("=" * 60)
        print("👉 现在请做以下操作：")
        print("   1. 打开 iPhone 蓝牙")
        print("   2. 打开 Cachito App")
        print("   3. 尝试连接并控制你的小猫爪")
        print()
        print("   能控制 → Venus 不是你的玩具")
        print("   不能控制 → Venus 就是你的玩具")
        print("=" * 60)
        print()
        print("测试完后按回车结束...")

        # 保持连接
        while True:
            try:
                await asyncio.sleep(2)
                if not client.is_connected:
                    print("⚠️  连接断开了！")
                    break
            except KeyboardInterrupt:
                break

    print("🔓 连接已释放")


if __name__ == "__main__":
    asyncio.run(main())
