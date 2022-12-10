from enum import IntEnum

class LedMsgType(IntEnum):
    """ Packet's type. """
    COMMAND = 0x33
    KEEP_ALIVE = 0xaa
    DIY = 0xa1

class LedCommand(IntEnum):
    """ A control command packet's type. """
    POWER      = 0x01
    BRIGHTNESS = 0x04
    COLOR      = 0x05

class LedMode(IntEnum):
    """
    The mode in which a color change happens in.
    
    Currently only manual is supported.
    """
    MANUAL     = 0x0d
    MICROPHONE = 0x06
    SCENES     = 0x05


READ_CHARACTERISTIC_UUIDS = ['00010203-0405-0607-0809-0a0b0c0d2b10']
WRITE_CHARACTERISTIC_UUIDS = ['00010203-0405-0607-0809-0a0b0c0d2b11']


# These values have been taken directly from the UI code of Govee's app
# The slider in the app returns one of these values

SHADES_OF_WHITE = [
    '#ff8d0b',
    '#ff8912',
    '#ff921d',
    '#ff8e21',
    '#ff9829',
    '#ff932c',
    '#ff9d33',
    '#ff9836',
    '#ffa23c',
    '#ff9d3f',
    '#ffa645',
    '#ffa148',
    '#ffaa4d',
    '#ffa54f',
    '#ffae54',
    '#ffa957',
    '#ffb25b',
    '#ffad5e',
    '#ffb662',
    '#ffb165',
    '#ffb969',
    '#ffb46b',
    '#ffbd6f',
    '#ffb872',
    '#ffc076',
    '#ffbb78',
    '#ffc37c',
    '#ffbe7e',
    '#ffc682',
    '#ffc184',
    '#ffc987',
    '#ffc489',
    '#ffcb8d',
    '#ffc78f',
    '#ffce92',
    '#ffc994',
    '#ffd097',
    '#ffcc99',
    '#ffd39c',
    '#ffce9f',
    '#ffd5a1',
    '#ffd1a3',
    '#ffd7a6',
    '#ffd3a8',
    '#ffd9ab',
    '#ffd5ad',
    '#ffdbaf',
    '#ffd7b1',
    '#ffddb4',
    '#ffd9b6',
    '#ffdfb8',
    '#ffdbba',
    '#ffe1bc',
    '#ffddbe',
    '#ffe2c0',
    '#ffdfc2',
    '#ffe4c4',
    '#ffe1c6',
    '#ffe5c8',
    '#ffe3ca',
    '#ffe7cc',
    '#ffe4ce',
    '#ffe8d0',
    '#ffe6d2',
    '#ffead3',
    '#ffe8d5',
    '#ffebd7',
    '#ffe9d9',
    '#ffedda',
    '#ffebdc',
    '#ffeede',
    '#ffece0',
    '#ffefe1',
    '#ffeee3',
    '#fff0e4',
    '#ffefe6',
    '#fff1e7',
    '#fff0e9',
    '#fff3ea',
    '#fff2ec',
    '#fff4ed',
    '#fff3ef',
    '#fff5f0',
    '#fff4f2',
    '#fff6f3',
    '#fff5f5',
    '#fff7f7',
    '#fff6f8',
    '#fff8f8',
    '#fff8fb',
    '#fff9fb',
    '#fff9fd',
    '#fff9fd',
    '#fef9ff',
    '#fefaff',
    '#fcf7ff',
    '#fcf8ff',
    '#f9f6ff',
    '#faf7ff',
    '#f7f5ff',
    '#f7f5ff',
    '#f5f3ff',
    '#f5f4ff',
    '#f3f2ff',
    '#f3f3ff',
    '#f0f1ff',
    '#f1f1ff',
    '#eff0ff',
    '#eff0ff',
    '#edefff',
    '#eeefff',
    '#ebeeff',
    '#eceeff',
    '#e9edff',
    '#eaedff',
    '#e7ecff',
    '#e9ecff',
    '#e6ebff',
    '#e7eaff',
    '#e4eaff',
    '#e5e9ff',
    '#e3e9ff',
    '#e4e9ff',
    '#e1e8ff',
    '#e3e8ff',
    '#e0e7ff',
    '#e1e7ff',
    '#dee6ff',
    '#e0e6ff',
    '#dde6ff',
    '#dfe5ff',
    '#dce5ff',
    '#dde4ff',
    '#dae4ff',
    '#dce3ff',
    '#d9e3ff',
    '#dbe2ff',
    '#d8e3ff',
    '#dae2ff',
    '#d7e2ff',
    '#d9e1ff',
    '#d6e1ff'
]

