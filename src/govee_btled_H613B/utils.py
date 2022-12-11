from colour import Color
import asyncio
from bleak import BleakClient, BleakScanner

def color2rgb(color):
    """ Converts a color-convertible into 3-tuple of 0-255 valued ints. """
    col = Color(color)
    rgb = col.red, col.green, col.blue
    rgb = [round(x * 255) for x in rgb]
    return tuple(rgb)


async def discover():
    """Discover Bluetooth LE devices."""
    devices = await BleakScanner.discover()
    return [device for device in devices if device.name.startswith("GBK_H613B_")]

def create_status_callback(future: asyncio.Future):
    def callback(sender: int, data: bytearray):
        if not future.done():
            future.set_result(data)
    return callback