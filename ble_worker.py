#!/usr/bin/env python3
"""
BLE advertiser worker process.
Reads intensity values from stdin, broadcasts to Venus via Service UUID advertising.
Runs NSRunLoop on main thread so CoreBluetooth callbacks work correctly.
"""
import sys
import random
import time
import objc
from Foundation import NSRunLoop, NSDate
import CoreBluetooth as CB

DEVICE_ID = "cbc5"


def build_uuid(intensity: int) -> str:
    rn = random.randint(0x64, 0xFF)
    did = bytes.fromhex(DEVICE_ID)
    i = max(0, min(100, intensity))
    if i == 0:
        # 停止命令：param1=0601，intensity=02
        payload = bytes([
            0x71, 0x00, 0x01, rn,
            0x04, 0x00,
            did[0], did[1],
            0x06, 0x01,
            0x02,
            0x00, 0x00, 0x00, 0x00,
        ])
    else:
        # 振动命令：param1=040a
        payload = bytes([
            0x71, 0x00, 0x01, rn,
            0x04, 0x00,
            did[0], did[1],
            0x04, 0x0a,
            i,
            0x00, 0x00, 0x00, 0x00,
        ])
    cs = sum(payload) & 0xFF
    h = (payload + bytes([cs])).hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# Initialize CoreBluetooth on main thread
CBDelegate = objc.protocolNamed('CBPeripheralManagerDelegate')

class Delegate(objc.lookUpClass('NSObject'), protocols=[CBDelegate]):
    def init(self):
        self = objc.super(Delegate, self).init()
        self.ready = False
        return self

    def peripheralManagerDidUpdateState_(self, mgr):
        state = mgr.state()
        self.ready = (state == 5)

    def peripheralManagerDidStartAdvertising_error_(self, mgr, error):
        pass


delegate = Delegate.alloc().init()
manager = CB.CBPeripheralManager.alloc().initWithDelegate_queue_options_(
    delegate, None, None
)

loop = NSRunLoop.currentRunLoop()
deadline = time.time() + 5.0
while not delegate.ready and time.time() < deadline:
    loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))

if not delegate.ready:
    print("ERROR: BT not ready", file=sys.stderr, flush=True)
    sys.exit(1)

print("READY", flush=True)

# Main command loop
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        intensity = int(line)
        for _ in range(3):
            uuid = CB.CBUUID.UUIDWithString_(build_uuid(intensity))
            manager.startAdvertising_({CB.CBAdvertisementDataServiceUUIDsKey: [uuid]})
            loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.3))
            manager.stopAdvertising()
            time.sleep(0.05)
        print("OK", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
