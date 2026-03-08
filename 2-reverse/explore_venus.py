#!/usr/bin/env python3
"""
Venus 设备探索器 — 连接你的小猫爪并发现完整 BLE 协议

使用方法：
1. 确保 Cachito App 已关闭
2. 小猫爪开机
3. 运行: python3 -m uv run explore_venus.py
"""

import asyncio
from bleak import BleakScanner, BleakClient

DEVICE_NAME = "Venus"


async def main():
    print("=" * 60)
    print("🐱 Venus (小猫爪) 专用探索器")
    print("=" * 60)

    # 扫描找到 Venus
    print("\n🔍 正在寻找 Venus 设备...")
    device = await BleakScanner.find_device_by_address("0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED", timeout=15.0)

    if not device:
        # 用前缀匹配
        print("   按地址没找到，尝试列出所有蓝牙名包含 'venus' 或为空的设备...")
        found = {}
        def cb(dev, adv):
            name = dev.name or adv.local_name or "Unknown"
            found[dev.address] = (name, dev)
            print(f"      发现: {name} - {dev.address}")
        scanner = BleakScanner(detection_callback=cb)
        await scanner.start()
        await asyncio.sleep(10)
        await scanner.stop()

        if found:
            # Let's just pick the first one that has venus in name, or ask user
            for addr, (name, dev) in found.items():
                if "venus" in name.lower() or name == "Unknown":
                    device = dev
                    break
        
        if not device:
            print("❌ 未找到 Venus 设备。请确认：")
            print("   1. 设备已开机")
            print("   2. Cachito App 已关闭")
            return

    print(f"✅ 找到设备: {device.name} ({device.address})")
    print(f"\n🔗 正在连接...")

    async with BleakClient(device.address, timeout=15.0) as client:
        if not client.is_connected:
            print("❌ 连接失败")
            return

        print("✅ 已连接！")
        print("\n" + "=" * 60)
        print("📋 完整 GATT 服务列表")
        print("=" * 60)

        all_writable = []

        for service in client.services:
            print(f"\n🔵 Service: {service.uuid}")
            print(f"   描述: {service.description or 'Custom/Unknown'}")

            for char in service.characteristics:
                props = ", ".join(char.properties)
                is_writable = "write" in char.properties or "write-without-response" in char.properties
                marker = "⭐" if is_writable else "  "

                print(f"   {marker} Characteristic: {char.uuid}")
                print(f"      属性: [{props}]")
                print(f"      Handle: 0x{char.handle:04X}")

                if is_writable:
                    all_writable.append(char)

                # 读取当前值
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        if value:
                            hex_str = value.hex(' ')
                            try:
                                text = value.decode('utf-8', errors='replace')
                                print(f"      值 (hex): {hex_str}")
                                print(f"      值 (text): {text}")
                            except:
                                print(f"      值: {hex_str}")
                        else:
                            print(f"      值: (空)")
                    except Exception as e:
                        print(f"      读取失败: {e}")

                # 列出描述符
                for desc in char.descriptors:
                    print(f"      📎 Descriptor: {desc.uuid}")
                    try:
                        val = await client.read_gatt_descriptor(desc.handle)
                        print(f"         值: {val.hex(' ')}")
                    except:
                        pass

        # 总结可写特征
        print("\n" + "=" * 60)
        print(f"📝 可写 Characteristics 总结 ({len(all_writable)} 个)")
        print("=" * 60)
        for i, char in enumerate(all_writable):
            props = ", ".join(char.properties)
            print(f"  [{i}] {char.uuid}")
            print(f"      属性: [{props}]")

        if all_writable:
            print("\n🧪 写入测试（找到控制通道）")
            print("   我会尝试向每个可写通道发送简单数据...")

            for i, char in enumerate(all_writable):
                try:
                    # 尝试写入 0x01 (通常是"开")
                    test_data = bytes([0x01])
                    response = "write-without-response" not in char.properties
                    await client.write_gatt_char(char.uuid, test_data, response=response)
                    print(f"  [{i}] {char.uuid} ← 写入 0x01 ✅ 成功!")
                    print(f"       👀 设备有反应吗？")
                    await asyncio.sleep(2)

                    # 写入 0x00 (通常是"关")
                    await client.write_gatt_char(char.uuid, bytes([0x00]), response=response)
                    print(f"       ← 写入 0x00 (关闭)")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"  [{i}] {char.uuid} ← 写入失败: {e}")

        print("\n✅ 探索完成！请把全部输出发给我。")
        print("   并告诉我：在写入测试中，设备有没有振动或反应？")


if __name__ == "__main__":
    asyncio.run(main())
