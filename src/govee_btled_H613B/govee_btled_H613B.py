import logging
from typing import Tuple
import traceback
import asyncio
import colorsys
from colour import Color
from collections.abc import Callable
from dataclasses import replace
import async_timeout

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakError,
    BleakNotFoundError,
    establish_connection,
    retry_bluetooth_connection_error,
)

from .const import (
    SHADES_OF_WHITE,
    READ_CHARACTERISTIC_UUIDS,WRITE_CHARACTERISTIC_UUIDS,
    LedCommand,LedMode,LedMsgType
)

from .exceptions import ConnectionTimeout,CharacteristicMissingError
from .utils import create_status_callback,color2rgb,discover
from .models import GoveeState

BLEAK_BACKOFF_TIME = 0.25

DISCONNECT_DELAY = 120

_LOGGER = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = 3


class GoveeInstance:
    def __init__(self, device: BLEDevice) -> None:
        self._ble_device = device
        self._client = BleakClientWithServiceCache(device)
        self._rgb_color = None
        self._brightness = None
        self._write_uuid = None
        self._read_uuid = None

        
        self._operation_lock = asyncio.Lock()
        self._state = GoveeState()
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._disconnect_timer = None
        self._expected_disconnect = False
        self.loop = asyncio.get_running_loop()
        self._callbacks: list[Callable[[GoveeState], None]] = []
    
    @property
    def address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._ble_device.name or self._ble_device.address

    @property
    def rssi(self) -> int | None:
        """Get the rssi of the device."""
        return self._ble_device.rssi

    @property
    def state(self) -> GoveeState:
        """Return the state."""
        return self._state

    
    @property
    def rgb(self) -> tuple[int, int, int]:
        return self._state.rgb

    @property
    def w(self) -> int:
        return self._state.w
    

    @property
    def on(self) -> bool:
        return self._state.power

    @property
    def brightness(self) -> int:
        """Return current brightness 0-255."""
        return self._state.brightness
    
    async def update(self) -> None:
        """Update the LEDBLE."""
        await self._ensure_connected()
        _LOGGER.debug("%s: Updating state", self.name)

        # Represent on state byte 3
        await self._send(LedMsgType.KEEP_ALIVE, 0x01, b'') # aa010000000000000000000000000000000000ab -> on:aa010100000000000000000000000000000000aa off:aa010000000000000000000000000000000000ab
        
        # These remained constant throughout my tests
        # await self._send(LedMsgType.KEEP_ALIVE, 0x06, b'') # aa060000000000000000000000000000000000ac -> aa06322e30342e3030000000000000000000009a
        # await self._send(LedMsgType.KEEP_ALIVE, 0x07, b'\x03') # aa070300000000000000000000000000000000ae -> aa0703322e30312e30310000000000000000009c
        # await self._send(LedMsgType.KEEP_ALIVE, 0x23, b'\xff') # aa23ff0000000000000000000000000000000076 -> aa23ff0000008000000080000000800000008076
        # await self._send(LedMsgType.KEEP_ALIVE, 0x12, b'') # aa120000000000000000000000000000000000b8 -> aa12ff640000800a0000000000000000000000a9
        # await self._send(LedMsgType.KEEP_ALIVE, 0x11, b'') # aa110000000000000000000000000000000000bb -> aa11001e0f0f00000000000000000000000000a5
        
        # unknown command
        # await self._send(LedMsgType.COMMAND, 0x09, bytes.fromhex('14030f0301010000000000000000000000'))
        

        await self._send(LedMsgType.KEEP_ALIVE, 0x05, b'\x01') # aa050100000000000000000000000000000000ae ->
        # byte 3 is always 0d

        # White mode, still don't know exactly the meaning of bytes 7-8
        # bytes 9-11 represent the array SHADES_OF_WHITE

        # in the set_white function I am doing something else: byte 7 is 0x01 and the bytes 8-10 are the SHADES_OF_WHITE
        # these values work, but the app doesn't read them, so certainly there was a change at some point

        # app values
        # aa 05 0d ff ff ff 07 d0 ff 89 12 00 00 00 00 00 00 00 00 ee (1% white)
        # aa 05 0d ff ff ff 23 28 d9 e1 ff 00 00 00 00 00 00 00 00 91 (100% white)
        # aa 05 0d ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00 00 5d (50% white)
        
        # set_white value
        # aa 05 0d ff ff ff 01 d6 e1 ff 00 00 00 00 00 00 00 00 00 94


        # Color mode rgb bytes 4-6

        # aa 05 0d ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 5d (red)
        # aa 05 0d 00 ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 5d (green)
        # aa 05 0d 00 ff ff 00 00 00 00 00 00 00 00 00 00 00 00 00 a2

        
        
        
        # Brightness test: in this one the byte 3 of the response is exactly the brightness percent
        
        await self._send(LedMsgType.KEEP_ALIVE, 0x04, b'')
        # aa040000000000000000000000000000000000ae -> aa04360000000000000000000000000000000098(54%) aa046400000000000000000000000000000000ca(100%) aa040100000000000000000000000000000000af(1%)
        
        


    
    
    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._ble_device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())

            self._client = client
            self._reset_disconnect_timer()

            _LOGGER.debug(
                "%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi
            )
            await client.start_notify(self._read_uuid, self._notification_handler)


    async def _send(self, head, cmd, payload):
        """ Sends a command and handles payload padding. """
        if not isinstance(cmd, int):
           raise ValueError('Invalid command')
        if not isinstance(payload, bytes) and not (isinstance(payload, list) and all(isinstance(x, int) for x in payload)):
            raise ValueError('Invalid payload')
        if len(payload) > 17:
            raise ValueError('Payload too long')

        cmd = cmd & 0xFF

        frame = bytes([head, cmd]) + bytes(payload)
        # pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        
        # The checksum is calculated by XORing all data bytes
        checksum = 0
        for b in frame:
            checksum ^= b
        
        frame += bytes([checksum & 0xFF])
        
        await self._ensure_connected()

        if not self._client.is_connected:
            _LOGGER.warn("Device not connected, dropping command")
        else:
            await self._send_command(frame)



    async def set_color(self, rgb: Tuple[int, int, int]):
        r, g, b = rgb
        # await self._write([0x56, r, g, b, 0x00, 0xF0, 0xAA])
        await self._send(LedMsgType.COMMAND, LedCommand.COLOR, [LedMode.MANUAL, r, g, b])
        self._state = replace(
            self._state,
            rgb= (r, g, b)
        )
        self._fire_callbacks()
    
    # although the device accepts values in the range [0, 255], it actually only does
    # anything useful with values from [1, 100], 
    # and this is exactly what the android app does
    async def set_brightness(self, intensity: int):
        _LOGGER.debug("%s: Set brightness: %s", self.name, intensity)
        if not 0 <= intensity <= 255:
            raise ValueError(f'Brightness value out of range: {intensity}')
        
        await self._send(LedMsgType.COMMAND, LedCommand.BRIGHTNESS, [intensity,])
        self._state = replace(self._state, brightness=intensity)
        self._fire_callbacks()
    
    async def set_white(self, intensity: int):
        _LOGGER.debug("%s: Set white: %s", self.name, intensity)
        """
        Sets the LED's color in white-mode.

        White mode seems to enable a different set of LEDs within the bulb.
        This method uses the hardcoded RGB values of whites, directly taken from
        the mechanism used in Govee's app.
        """
        if not 0 <= intensity <= 255:
            raise ValueError(f'White value out of range: {value}')
        value = (intensity) / 255 # in [0.0, 1.0]
        index = round(value * (len(SHADES_OF_WHITE)-1))
        white = Color(SHADES_OF_WHITE[index])
        
        # Set the color to white (although ignored) and the boolean flag to True
        await self._send(LedMsgType.COMMAND, LedCommand.COLOR, [LedMode.MANUAL, 0xff, 0xff, 0xff, 0x01, *color2rgb(white)])
        self._state = replace(
            self._state,
            rgb=(0xff, 0xff, 0xff),
            brightness=intensity
        )
        self._fire_callbacks()

    async def turn_on(self):
        _LOGGER.debug("%s: Turn on", self.name)
        await self._send(LedMsgType.COMMAND, LedCommand.POWER, [0x1])
        self._state = replace(self._state, power=True)
        self._fire_callbacks()
        
    async def turn_off(self):
        _LOGGER.debug("%s: Turn off", self.name)
        await self._send(LedMsgType.COMMAND, LedCommand.POWER, [0x0])
        self._state = replace(self._state, power=False)
        self._fire_callbacks()

    

    async def disconnect(self):
        _LOGGER.debug("%s: Disconnect", self.name)
        await self._execute_disconnect()
    
    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""

        _LOGGER.debug("%s: Notification received: %s", self.name, data.hex())
        
        
        if data[0] == LedMsgType.KEEP_ALIVE:

            if data[1] == LedCommand.POWER:
                self._state = replace(self._state, power=(data[2] == 0x01))
            elif data[1] == LedCommand.COLOR:
                if data[2] != 0x0d:
                    _LOGGER.warn('Unknown byte 3 seen in COLOR info packet', data[2])
                else:
                    self._state = replace(self._state, rgb=(data[3], data[4], data[5]))
                    # for now not taking care of white color parameter nor updating w_index
            elif data[1] == LedCommand.BRIGHTNESS:
                self._state = replace(self._state, brightness=data[2])
            
            _LOGGER.debug(
                "%s: Notification received; RSSI: %s: %s %s",
                self.name,
                self.rssi,
                data.hex(),
                self._state,
            )

        self._fire_callbacks()
    
    def _reset_disconnect_timer(self) -> None:
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        else:
            _LOGGER.debug(
                "%s: Device unexpectedly disconnected; RSSI: %s",
                self.name,
                self.rssi,
            )

    def _disconnect(self) -> None:
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            read_char = self._read_uuid
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._read_uuid = None
            self._write_uuid = None
            if client and client.is_connected:
                await client.stop_notify(read_char)
                await client.disconnect()


    @retry_bluetooth_connection_error(DEFAULT_ATTEMPTS)
    async def _send_command_locked(self, commands: list[bytes]) -> None:
        """Send command to device and read response."""
        try:
            await self._execute_command_locked(commands)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                BLEAK_BACKOFF_TIME,
                ex,
            )
            await self._execute_disconnect()
            raise
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_disconnect()
            raise


    async def _send_command(
        self, commands: list[bytes] | bytes, retry: int | None = None
    ) -> None:
        """Send command to device and read response."""
        await self._ensure_connected()
        if not isinstance(commands, list):
            commands = [commands]
        await self._send_command_while_connected(commands, retry)

    async def _send_command_while_connected(
        self, commands: list[bytes], retry: int | None = None
    ) -> None:
        """Send command to device and read response."""
        _LOGGER.debug(
            "%s: Sending commands %s",
            self.name,
            [command.hex() for command in commands],
        )
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            try:
                await self._send_command_locked(commands)
                return
            except BleakNotFoundError:
                _LOGGER.error(
                    "%s: device not found, no longer in range, or poor RSSI: %s",
                    self.name,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except CharacteristicMissingError as ex:
                _LOGGER.debug(
                    "%s: characteristic missing: %s; RSSI: %s",
                    self.name,
                    ex,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except BLEAK_EXCEPTIONS:
                _LOGGER.debug("%s: communication failed", self.name, exc_info=True)
                raise

        raise RuntimeError("Unreachable")


    async def _execute_command_locked(self, commands: list[bytes]) -> None:
        """Execute command and read response."""
        assert self._client is not None  # nosec
        if not self._read_uuid:
            raise CharacteristicMissingError("Read characteristic missing")
        if not self._write_uuid:
            raise CharacteristicMissingError("Write characteristic missing")
        for command in commands:
            await self._client.write_gatt_char(self._write_uuid, command, False)

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Resolve characteristics."""
        for characteristic in READ_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._read_uuid = char
                break
        for characteristic in WRITE_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._write_uuid = char
                break
        return bool(self._read_uuid and self._write_uuid)
    
    def _fire_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._callbacks:
            callback(self._state)

    def register_callback(
        self, callback: Callable[[GoveeState], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._callbacks.remove(callback)

        self._callbacks.append(callback)
        return unregister_callback