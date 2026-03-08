import asyncio
from bleak import BleakClient

ADDRESS = "0796E6C5-74BB-A5BB-9E48-1FD9F83D9AED"

# Unlocked characteristics
OPEN_1 = "06aa3a41-f22a-11e3-9daa-0002a5d5c51b"
OPEN_2 = "06aa3a61-f22a-11e3-9daa-0002a5d5c51b"
OPEN_3 = "43af0001-5c58-4180-a3e4-471d6a45e2de"

# Typical locked characteristic containing control
CONTROL_GUESS = "06aa3a42-f22a-11e3-9daa-0002a5d5c51b"
CONTROL_GUESS_2 = "06aa3a44-f22a-11e3-9daa-0002a5d5c51b"

TOKEN_B = bytes.fromhex("cb 1a a4 65 a1 50 d4 22 9e 8b 42 18 26 b2 e4 d3 8c 52 ab 3a")

async def test():
    print("Connecting...")
    async with BleakClient(ADDRESS, timeout=10.0) as client:
        print("Connected.")
        
        # Test if control is locked
        try:
            await client.write_gatt_char(CONTROL_GUESS, bytes([0x00, 0x00, 0x00, 0xB0]), response=True)
            print("Wait, CONTROL_GUESS is already unlocked!?")
        except Exception as e:
            print(f"CONTROL_GUESS is locked as expected.")
            
        print("\nAttempting to unlock using OPEN_1...")
        await client.write_gatt_char(OPEN_1, TOKEN_B, response=False)
        await asyncio.sleep(1)
        
        try:
            await client.write_gatt_char(CONTROL_GUESS, bytes([0x00, 0x00, 0x00, 0xB0]), response=True)
            print("SUCCESS! OPEN_1 is the auth channel and CONTROL_GUESS unlocked! Toy should vibrate.")
            await asyncio.sleep(2)
            await client.write_gatt_char(CONTROL_GUESS, bytes([0x00, 0x00, 0x00, 0xA3]), response=False)
            return
        except:
            print("Failed. OPEN_1 didn't unlock CONTROL_GUESS.")
            
        try:
            await client.write_gatt_char(CONTROL_GUESS_2, bytes([0x00, 0x00, 0x00, 0xB0]), response=True)
            print("SUCCESS! OPEN_1 is the auth channel and CONTROL_GUESS_2 unlocked! Toy should vibrate.")
            await asyncio.sleep(2)
            await client.write_gatt_char(CONTROL_GUESS_2, bytes([0x00, 0x00, 0x00, 0xA3]), response=False)
            return
        except:
            print("Failed. OPEN_1 didn't unlock CONTROL_GUESS_2 either.")
            
        print("\nAttempting to unlock using OPEN_2...")
        await client.write_gatt_char(OPEN_2, TOKEN_B, response=False)
        await asyncio.sleep(1)
        
        try:
            await client.write_gatt_char(CONTROL_GUESS, bytes([0x00, 0x00, 0x00, 0xB0]), response=True)
            print("SUCCESS! OPEN_2 is the auth channel! Toy should vibrate.")
            await asyncio.sleep(2)
            await client.write_gatt_char(CONTROL_GUESS, bytes([0x00, 0x00, 0x00, 0xA3]), response=False)
            return
        except:
            print("Failed. OPEN_2 didn't unlock CONTROL_GUESS.")

asyncio.run(test())
