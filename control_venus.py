#!/usr/bin/env python3
"""
Control Venus (小猫爪) from Mac via BLE Service UUID advertising.

Usage:
  python3 control_venus.py vibrate 50      # 50% intensity
  python3 control_venus.py stop
  python3 control_venus.py demo
"""
import random
import time
import sys

DEVICE_ID = "cbc5"  # captured from sniff_cachito.py

# ── Command builder ────────────────────────────────────────────────────────────

def build_uuid(intensity: int, cmd_code: bytes = b'\x04\x00',
               param1: bytes = b'\x04\x0a') -> str:
    rn = random.randint(0x64, 0xFF)
    did = bytes.fromhex(DEVICE_ID)
    i = max(0, min(100, intensity))
    payload = bytes([
        0x71, 0x00, 0x01, rn,
        cmd_code[0], cmd_code[1],
        did[0], did[1],
        param1[0], param1[1],
        i,
        0x00, 0x00, 0x00, 0x00,
    ])
    cs = sum(payload) & 0xFF
    h = (payload + bytes([cs])).hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

# ── CoreBluetooth singleton ────────────────────────────────────────────────────

_manager = None
_delegate = None

def _init_ble():
    global _manager, _delegate
    if _manager is not None:
        return

    try:
        import objc
        from Foundation import NSRunLoop, NSDate
        import CoreBluetooth as CB
    except ImportError:
        print("ERROR: pip3 install pyobjc-framework-CoreBluetooth")
        sys.exit(1)

    CBPeripheralManagerDelegate = objc.protocolNamed('CBPeripheralManagerDelegate')

    class _VenusDelegate(objc.lookUpClass('NSObject'),
                         protocols=[CBPeripheralManagerDelegate]):
        def init(self):
            self = objc.super(_VenusDelegate, self).init()
            self.powered_on = False
            return self

        def peripheralManagerDidUpdateState_(self, manager):
            self.powered_on = (manager.state() == 5)

        def peripheralManagerDidStartAdvertising_error_(self, manager, error):
            if error:
                print(f"  Advertise error: {error.localizedDescription()}")

    _delegate = _VenusDelegate.alloc().init()
    _manager = CB.CBPeripheralManager.alloc().initWithDelegate_queue_options_(
        _delegate, None, None
    )

    # Wait for BT to power on
    from Foundation import NSRunLoop, NSDate
    deadline = time.time() + 3.0
    while not _delegate.powered_on and time.time() < deadline:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05))

    if not _delegate.powered_on:
        print("ERROR: Bluetooth not ready")
        sys.exit(1)


def advertise_uuid(uuid_str: str, duration: float = 0.4):
    import CoreBluetooth as CB
    from Foundation import NSRunLoop, NSDate

    _manager.stopAdvertising()
    time.sleep(0.05)

    uuid = CB.CBUUID.UUIDWithString_(uuid_str)
    _manager.startAdvertising_({CB.CBAdvertisementDataServiceUUIDsKey: [uuid]})

    end = time.time() + duration
    while time.time() < end:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05))

    _manager.stopAdvertising()


# ── Commands ───────────────────────────────────────────────────────────────────

def send_vibrate(intensity: int, repeat: int = 3):
    print(f"Vibrate {intensity}%")
    for _ in range(repeat):
        uuid = build_uuid(intensity)
        print(f"  → {uuid}")
        advertise_uuid(uuid, duration=0.3)
        time.sleep(0.05)


def send_stop(repeat: int = 3):
    print("Stop")
    for _ in range(repeat):
        uuid = build_uuid(0)
        print(f"  → {uuid}")
        advertise_uuid(uuid, duration=0.3)
        time.sleep(0.05)


def demo():
    print("Demo: ramp up then down")
    for i in range(0, 101, 20):
        send_vibrate(i, repeat=2)
        time.sleep(0.5)
    for i in range(100, -1, -20):
        send_vibrate(i, repeat=2)
        time.sleep(0.5)
    send_stop()


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    _init_ble()

    cmd = args[0].lower()
    if cmd == "vibrate":
        intensity = int(args[1]) if len(args) > 1 else 50
        send_vibrate(intensity)
    elif cmd == "stop":
        send_stop()
    elif cmd == "demo":
        demo()
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)
