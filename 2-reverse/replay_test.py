#!/usr/bin/env python3
"""
Venus 协议重放测试 — 基于 sysdiagnose HCI 抓包分析

从 HCI log 提取的 ATT Handle:
  0x0019 (25)  = 认证通道 (20字节令牌)
  0x0033 (51)  = 控制命令 (4字节: 00 00 00 XX)
  0x0002 (2)   = 心跳/配置
  0x009C (156) = 初始配对令牌 (仅1次)

运行前: iPhone 蓝牙关闭, 小猫爪开机
"""

import asyncio
from bleak import BleakScanner, BleakClient

DEVICE_ADDRESS = "0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED"

# 从 HCI log 提取的认证令牌 (均为 20 字节)
TOKEN_A = bytes.fromhex("4ca29784f3d5bada8ad1ba28df7e32005f1a4799")   # 出现 2 次
TOKEN_B = bytes.fromhex("cb1aa465a150d4229e8b421826b2e4d38c52ab3a")   # 出现 20 次
TOKEN_C = bytes.fromhex("d6cc65cc842136394736bf5e4197c8c3867d7bc3")   # 出现 15 次

# 初始配对令牌 (连接开头仅出现 1 次)
PAIRING_TOKEN = bytes.fromhex("c0d59153304189582438b70ba0b9f2a78fa99987")

# 心跳包 (20字节全0)
HEARTBEAT = bytes(20)


async def w(client, handle, data, label=""):
    try:
        await client.write_gatt_char(handle, data, response=True)
        print(f"  OK  {handle:#06x} <- {data.hex(' ')}  {label}")
        return True
    except Exception as e:
        print(f"  ERR {handle:#06x} : {e}")
        return False


async def main():
    print("=" * 60)
    print("Venus 小猫爪 协议重放测试")
    print("=" * 60)
    print("确保: iPhone 蓝牙已关闭, 小猫爪已开机")
    input("准备好后按回车...")

    print("\n扫描中 (最多 60 秒)...")
    device = None

    def cb(dev, adv):
        nonlocal device
        if dev.address == DEVICE_ADDRESS:
            device = dev
            print(f"  找到! {dev.name}  {adv.rssi} dBm")

    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    for i in range(60):
        if device:
            break
        await asyncio.sleep(1)
        print(f"\r  等待 {i+1}/60s...", end="", flush=True)
    await scanner.stop()

    if not device:
        print("\n未找到设备")
        return

    print("\n连接中...")
    async with BleakClient(DEVICE_ADDRESS, timeout=20.0) as client:
        print("已连接!\n")

        # 打印 handle 映射，用于验证
        print("--- Handle 映射 ---")
        for svc in client.services:
            for char in svc.characteristics:
                print(f"  {char.handle:#06x} ({char.handle:3d})  {char.uuid}  [{', '.join(char.properties)}]")
        print("---\n")

        # Step 1: 初始配对令牌
        print("[Step 1] 初始配对令牌 -> 0x009C")
        await w(client, 0x009C, PAIRING_TOKEN)
        await asyncio.sleep(0.5)

        # Step 2: 认证令牌序列
        print("\n[Step 2] 认证令牌 -> 0x0019")
        await w(client, 0x0019, TOKEN_A, "Token A")
        await asyncio.sleep(0.2)
        for i in range(3):
            await w(client, 0x0019, TOKEN_B, f"Token B #{i+1}")
            await asyncio.sleep(0.2)
        await w(client, 0x0019, TOKEN_C, "Token C")
        await asyncio.sleep(0.5)

        # Step 3: 控制命令
        print("\n[Step 3] 控制命令 -> 0x0033  (有振动请告诉我哪个!)")
        for xx in [0xA3, 0xA8, 0xAF, 0xB5, 0xBD]:
            cmd = bytes([0x00, 0x00, 0x00, xx])
            ok = await w(client, 0x0033, cmd, f"XX={xx:#04x}")
            if ok:
                print(f"  >>> 等 2 秒，有振动吗? <<<")
                await asyncio.sleep(2)
                await w(client, 0x0033, bytes(4), "停止")
                await asyncio.sleep(1)

        print("\n测试完成! 请把输出发给我，并告诉我哪一步有振动。")


if __name__ == "__main__":
    asyncio.run(main())
