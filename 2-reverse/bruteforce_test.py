#!/usr/bin/env python3
"""
Venus 协议暴力测试器

尝试各种常见 BLE 玩具命令格式，找出哪个能让设备振动。
"""

import asyncio
from bleak import BleakScanner, BleakClient

DEVICE_ADDRESS = "0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED"

# 之前成功写入的通道
WRITE_CHARS = [
    "06aa3a41-f22a-11e3-9daa-0002a5d5c51b",  # [0] write only
    "06aa3a61-f22a-11e3-9daa-0002a5d5c51b",  # [1] write only
    "43af0001-5c58-4180-a3e4-471d6a45e2de",  # [18] notify+write+read
]

# 之前被拒绝的通道 - 尝试 write-without-response 模式
LOCKED_CHARS = [
    "06aa3a42-f22a-11e3-9daa-0002a5d5c51b",
    "06aa3a19-f22a-11e3-9daa-0002a5d5c51b",
    "06aa3a39-f22a-11e3-9daa-0002a5d5c51b",
    "06aa3a59-f22a-11e3-9daa-0002a5d5c51b",
    "06aa3a79-f22a-11e3-9daa-0002a5d5c51b",
    "06aa3a2a-f22a-11e3-9daa-0002a5d5c51b",
]

# 常见 BLE 玩具命令格式
TEST_COMMANDS = [
    # 简单强度值
    ("单字节强度", [
        bytes([0x01]), bytes([0x05]), bytes([0x0A]),
        bytes([0x32]), bytes([0x50]), bytes([0x64]), bytes([0xFF]),
    ]),
    # 模式+强度 双字节
    ("模式+强度", [
        bytes([0x01, 0x05]), bytes([0x01, 0x32]), bytes([0x01, 0x64]),
        bytes([0x01, 0xFF]), bytes([0x02, 0x05]), bytes([0x03, 0x05]),
    ]),
    # 带头部的命令
    ("带AA头", [
        bytes([0xAA, 0x01]), bytes([0xAA, 0x01, 0x05]),
        bytes([0xAA, 0x01, 0x32]), bytes([0xAA, 0x01, 0x64]),
    ]),
    # 带FF头
    ("带FF头", [
        bytes([0xFF, 0x01]), bytes([0xFF, 0x01, 0x05]),
        bytes([0xFF, 0x03, 0x01, 0x05]),
    ]),
    # Lovense 类似格式 (ASCII命令)
    ("ASCII命令", [
        b"Vibrate:5;", b"Vibrate:10;", b"Vibrate:20;",
        b"PowerOn;", b"Status;",
    ]),
    # 常见IoT命令格式
    ("IoT格式", [
        bytes([0x55, 0xAA, 0x01, 0x01, 0x01]),
        bytes([0x55, 0xAA, 0x01, 0x05, 0x01]),
        bytes([0xA5, 0x01, 0x01, 0x00]),
        bytes([0x5A, 0xA5, 0x01, 0x05]),
    ]),
    # 特定模式：设备可能需要长命令
    ("长格式命令", [
        bytes([0x01] * 8),
        bytes([0x01, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]),
        bytes([0x01, 0x01, 0x00, 0x00, 0x32, 0x00, 0x00, 0x00]),
        bytes([0x00, 0x01, 0x05, 0x00, 0x00, 0x00]),
        bytes(range(12)),  # 0x00-0x0B，12字节
    ]),
]


async def main():
    print("=" * 60)
    print("🧪 Venus 协议暴力测试")
    print("=" * 60)
    print("\n⚠️  iPhone 蓝牙关闭，小猫爪开机")
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
        print("\n❌ 未找到")
        return

    print(f"\n✅ 找到！连接中...")

    async with BleakClient(DEVICE_ADDRESS, timeout=20.0) as client:
        print("✅ 已连接\n")

        # 先订阅通知
        print("📡 订阅通知通道...\n")
        notify_chars = [
            "06aa3a51-f22a-11e3-9daa-0002a5d5c51b",
            "06aa3a12-f22a-11e3-9daa-0002a5d5c51b",
            "06aa3a22-f22a-11e3-9daa-0002a5d5c51b",
            "06aa3a23-f22a-11e3-9daa-0002a5d5c51b",
            "06aa3a29-f22a-11e3-9daa-0002a5d5c51b",
            "06aa3a49-f22a-11e3-9daa-0002a5d5c51b",
        ]

        def notify_handler(sender, data):
            print(f"   📥 收到通知 {sender}: {data.hex(' ')}")

        for nc in notify_chars:
            try:
                await client.start_notify(nc, notify_handler)
            except:
                pass

        # ===== 测试已开放的写通道 =====
        print("=" * 60)
        print("📝 测试已开放的 3 个写通道")
        print("=" * 60)

        for char_uuid in WRITE_CHARS:
            short = char_uuid.split('-')[0]
            print(f"\n{'─' * 40}")
            print(f"通道: {short}")

            for group_name, cmds in TEST_COMMANDS:
                found_reaction = False
                for cmd in cmds:
                    try:
                        await client.write_gatt_char(char_uuid, cmd, response=False)
                        print(f"  ← {group_name}: {cmd.hex(' ')} ✅")
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        # 尝试 with response
                        try:
                            await client.write_gatt_char(char_uuid, cmd, response=True)
                            print(f"  ← {group_name}: {cmd.hex(' ')} ✅ (w/resp)")
                            await asyncio.sleep(1.5)
                        except:
                            pass

                # 写入 0x00 关闭
                try:
                    await client.write_gatt_char(char_uuid, bytes([0x00]), response=False)
                except:
                    pass

        # ===== 尝试 write-without-response 绕过锁定 =====
        print(f"\n{'=' * 60}")
        print("🔓 尝试绕过锁定通道 (write-without-response)")
        print("=" * 60)

        for char_uuid in LOCKED_CHARS:
            short = char_uuid.split('-')[0]
            for cmd in [bytes([0x01]), bytes([0x05]), bytes([0x32]), bytes([0xFF])]:
                try:
                    await client.write_gatt_char(char_uuid, cmd, response=False)
                    print(f"  {short} ← {cmd.hex(' ')} ✅")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"  {short} ← {cmd.hex(' ')} ❌ {str(e)[:50]}")
                    break

        print(f"\n{'=' * 60}")
        print("✅ 测试完成！")
        print("   请告诉我：全程设备有没有【任何反应】？")
        print("   振动、声音、灯光变化 都算！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
