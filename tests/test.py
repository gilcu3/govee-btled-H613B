#! /usr/bin/env python3
import asyncio

import logging
from govee_btled_H613B import GoveeInstance
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
import asyncio

# Add here the mac address of the device to test
MAC_ADDRESS = ''

logging.basicConfig()
logging.getLogger('govee_btled_H613B').setLevel(logging.DEBUG)

async def main():
    delay = 1

    scanner = BleakScanner()
    b = await scanner.find_device_by_address(MAC_ADDRESS)
    led = GoveeInstance(b)
    await led.turn_on()
    await asyncio.sleep(delay)
    await led.update()
    await asyncio.sleep(delay)
    await led.set_white(100)
    await asyncio.sleep(delay)
    await led.update()
    await asyncio.sleep(delay)
    await led.set_white(100)
    await led.update()
    await asyncio.sleep(delay)
    await led.set_white(1)
    await led.update()
    await led.set_brightness(255)
    await asyncio.sleep(delay)
    await led.set_color((0, 0, 255))
    await led.update()
    await asyncio.sleep(delay)
    await led.set_color((255, 0, 0))
    await led.update()
    await asyncio.sleep(delay)
    await led.set_color((0, 255, 0))
    await led.update()
    await asyncio.sleep(delay)
    await led.set_brightness(0)
    await led.update()
    await asyncio.sleep(delay)
    await led.turn_off()
    await asyncio.sleep(delay)
    await led.update()
    await asyncio.sleep(delay)
    await led.disconnect()
if __name__ == '__main__':
    asyncio.run(main())
