#!/usr/bin/env python3
"""
BLE 对比扫描 + 自动探索（加长版）

使用方法：
1. 彻底关掉 Cachito App（后台划掉）
2. 小猫爪先【关机】
3. 运行此脚本，按提示操作
"""

import asyncio
from bleak import BleakScanner, BleakClient


async def long_scan(seconds=35):
    """长时间扫描，返回 {address: (name, rssi, svc_uuids, device)}"""
    found = {}
    def cb(dev, adv):
        # 持续更新（取最新的 rssi 和 name）
        name = dev.name or adv.local_name
        found[dev.address] = (name, adv.rssi, adv.service_uuids or [], dev, adv.manufacturer_data)
    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    for i in range(seconds):
        await asyncio.sleep(1)
        print(f"\r   扫描中... {i+1}/{seconds}秒 | 已发现 {len(found)} 个设备", end="", flush=True)
    await scanner.stop()
    print()
    return found


async def explore_device(device):
    """连接设备并列出全部 GATT 服务"""
    print(f"\n   🔗 连接 {device.name or device.address}...")
    try:
        async with BleakClient(device.address, timeout=12.0) as client:
            if not client.is_connected:
                print("   ❌ 连接失败")
                return

            print("   ✅ 已连接！GATT 服务：\n")
            writable = []

            for service in client.services:
                print(f"   🔵 Service: {service.uuid}")
                print(f"      描述: {service.description or 'Unknown'}")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    is_w = "write" in char.properties or "write-without-response" in char.properties
                    mark = "⭐" if is_w else "  "
                    print(f"   {mark} Char: {char.uuid}  [{props}]")
                    if is_w:
                        writable.append(char)
                    if "read" in char.properties:
                        try:
                            v = await client.read_gatt_char(char.uuid)
                            if v:
                                print(f"         值: {v.hex(' ')}")
                                try:
                                    t = v.decode('utf-8', errors='ignore').strip('\x00')
                                    if t and t.isprintable():
                                        print(f"         文本: {t}")
                                except:
                                    pass
                        except:
                            pass

            print(f"\n   📝 可写通道: {len(writable)} 个")
            for i, c in enumerate(writable):
                print(f"      [{i}] {c.uuid}  [{', '.join(c.properties)}]")

            # 写入测试
            if writable:
                print(f"\n   🧪 开始写入测试（可能触发振动！）")
                for i, c in enumerate(writable):
                    try:
                        resp = "write-without-response" not in c.properties
                        await client.write_gatt_char(c.uuid, bytes([0x01]), response=resp)
                        print(f"      [{i}] {c.uuid} ← 0x01 ✅ （看设备有没有反应！）")
                        await asyncio.sleep(3)
                        await client.write_gatt_char(c.uuid, bytes([0x00]), response=resp)
                        print(f"          ← 0x00 (关)")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"      [{i}] {c.uuid} ← 失败: {e}")

    except asyncio.TimeoutError:
        print("   ⏳ 连接超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


async def main():
    print("=" * 60)
    print("🐱 小猫爪 BLE 对比扫描 + 自动探索（加长版）")
    print("=" * 60)

    # ===== Phase 1: 开机扫描 =====
    print("\n🔛 Step 1: 请确保：")
    print("   • 小猫爪【开机】")
    print("   • Cachito App 已从后台彻底划掉")
    input("\n   准备好后按回车... ")

    print(f"\n🔍 扫描所有设备（35秒）...")
    with_device = await long_scan()
    print(f"   ✅ 开机状态: {len(with_device)} 个设备\n")

    # ===== Phase 2: 关机扫描 =====
    print("=" * 60)
    print("📵 Step 2: 现在请【关掉小猫爪】")
    print("   关机后等 3-5 秒再按回车")
    input("\n   准备好后按回车... ")

    print(f"\n🔍 重新扫描（35秒）...")
    without_device = await long_scan()
    print(f"   ✅ 关机状态: {len(without_device)} 个设备\n")

    # ===== 对比：找消失的设备 =====
    disappeared = []
    for addr, info in with_device.items():
        if addr not in without_device:
            disappeared.append(info)

    # 按信号强度排序
    disappeared.sort(key=lambda x: x[1] if x[1] else -999, reverse=True)

    if not disappeared:
        print("⚠️  没有发现消失的设备！")
        print("   可能的原因：")
        print("   1. Cachito App 还在后台连着设备（iPhone 设置→通用→后台App刷新→关掉 Cachito）")
        print("   2. 设备关机不够彻底")
        print("   3. 试试重启设备再来一次")
        return

    print("=" * 60)
    print(f"🎯 关机后消失了 {len(disappeared)} 个设备！其中就有你的小猫爪：")
    print("=" * 60)

    for i, (name, rssi, svcs, dev, mfr) in enumerate(disappeared):
        display = name or "(未知)"
        print(f"\n  [{i}] {display} | {rssi} dBm | {dev.address}")
        if svcs:
            for s in svcs:
                print(f"      服务: {s}")
        if mfr:
            for mid, data in mfr.items():
                print(f"      厂商 0x{mid:04X}: {data.hex(' ')}")

    # 重新开机再连接探索
    print("\n" + "=" * 60)
    print("🔛 Step 3: 请重新【打开小猫爪】以便连接探索")
    input("   开机后按回车... ")

    print("🔍 短暂扫描找到设备...")
    scan3 = await long_scan(10)

    print("\n🔍 自动探索消失过的设备...")
    print("=" * 60)

    explored = 0
    for name, rssi, svcs, dev, mfr in disappeared:
        # 跳过明显的 Apple 设备
        if mfr and 0x004C in mfr and not name:
            continue
        if name and any(k in name.lower() for k in ["iphone", "ipad", "macbook", "bose", "samsung", "airpod"]):
            continue

        # 需要重新获取设备引用（因为重新开机了）
        if dev.address in scan3:
            fresh_dev = scan3[dev.address][3]
        else:
            print(f"\n  ⚠️ {name or '(未知)'} 未重新出现，跳过")
            continue

        explored += 1
        print(f"\n{'─' * 50}")
        print(f"  {name or '(未知)'} | {rssi} dBm")
        await explore_device(fresh_dev)

        if explored >= 5:
            break

    print("\n" + "=" * 60)
    print("✅ 完成！请把全部输出发给我")
    print("   并告诉我：设备有没有在哪一步振动？")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
