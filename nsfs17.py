#!/usr/bin/python3

"""
MIT License

Copyright (c) 2020 gdsports625@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""

Adapt various USB joystick controllers for use with a Nintendo Switch (NS)
console.  All controllers are active but are seen by the console as one
controller so co-pilot mode is always active.

Read from joysticks and write to NSGadget device. The following joysticks are
supported

* Hori HoriPad gamepad
* Xbox One gamepads
* PS4 gamepad
* Logitech Extreme 3D Pro flightstick
* Thrustmaster T.16000M flightstick
* Dragon Rise arcade joysticks

NSGadget is an Adafruit Trinket M0 emulating an NS compatible gamepad. The
connection to between the Pi and NSGadget is 2 Mbits/sec UART.

"""
import os
import time
import sys
import getopt
from struct import unpack
import threading
import array
from fcntl import ioctl
import serial
from gpiozero import Button
from nsgpadserial import NSGamepadSerial, NSButton, NSDPad
import mido

# Map the 4 direction buttons (up, right, down, left) to NS direction pad values
BUTTONS_MAP_DPAD = array.array('B', [
    # U = Up button, R = right button, etc
    #                     LDRU
    NSDPad.CENTERED,    # 0000
    NSDPad.UP,          # 0001
    NSDPad.RIGHT,       # 0010
    NSDPad.UP_RIGHT,    # 0011
    NSDPad.DOWN,        # 0100
    NSDPad.CENTERED,    # 0101
    NSDPad.DOWN_RIGHT,  # 0110
    NSDPad.CENTERED,    # 0111
    NSDPad.LEFT,        # 1000
    NSDPad.UP_LEFT,     # 1001
    NSDPad.CENTERED,    # 1010
    NSDPad.CENTERED,    # 1011
    NSDPad.DOWN_LEFT,   # 1100
    NSDPad.CENTERED,    # 1101
    NSDPad.CENTERED,    # 1110
    NSDPad.CENTERED     # 1111
])

NSG = NSGamepadSerial()
try:
    # Raspberry Pi UART on pins 14,15
    NS_SERIAL = serial.Serial('/dev/ttyAMA0', 2000000, timeout=0)
    print("Found ttyAMA0")
except:
    try:
        # CP210x is capable of 2,000,000 bits/sec
        NS_SERIAL = serial.Serial('/dev/ttyUSB0', 2000000, timeout=0)
        print("Found ttyUSB0")
    except:
        print("NSGadget serial port not found")
        sys.exit(1)
NSG.begin(NS_SERIAL)

def read_horipad(jsdev):
    """
    The Hori HoriPad is a Nintendo Switch compatible gamepad.
    Buttons and axes are mapped straight through so this is
    the easiest. Runs as a thread
    """
    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                if value:
                    NSG.press(number)
                else:
                    NSG.release(number)

            if type == 0x02: # axis event
                axis = ((value + 32768) >> 8)
                # Axes 0,1 left stick X,Y
                if number == 0:
                    NSG.leftXAxis(axis)
                elif number == 1:
                    NSG.leftYAxis(axis)
                # Axes 2,3 right stick X,Y
                elif number == 2:
                    NSG.rightXAxis(axis)
                elif number == 3:
                    NSG.rightYAxis(axis)
                # Axes 4,5 directional pad X,Y
                elif number == 4:
                    NSG.dPadXAxis(axis)
                elif number == 5:
                    NSG.dPadYAxis(axis)

def read_xbox1(jsdev):
    """
    The Xbox One controller has fewer buttons and the throttles are analog instead of buttons.
    Runs as a thread
    axis    0: left stick X
            1: left stick Y
            2: left throttle
            3: right stick X
            4: right stick Y
            5: right throttle
            6: dPad X
            7: dPad Y

    button  0: A                NS B
            1: B                NS A
            2: X                NS Y
            3: Y                NS X
            4: left trigger     NS left trigger
            5: right trigger    NS right trigger
            6: windows          NS minus
            7: lines            NS plus
            8: logo             NS home
            9: left stick button  NS left stick
           10: right stick button NS right stick

    windows lines

        Y
    X       B
        A
    """
    BUTTON_MAP = array.array('B', [
        NSButton.B,
        NSButton.A,
        NSButton.Y,
        NSButton.X,
        NSButton.LEFT_TRIGGER,
        NSButton.RIGHT_TRIGGER,
        NSButton.MINUS,
        NSButton.PLUS,
        NSButton.HOME,
        NSButton.LEFT_STICK,
        NSButton.RIGHT_STICK])

    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                button_out = BUTTON_MAP[number]
                if value:
                    NSG.press(button_out)
                else:
                    NSG.release(button_out)

            if type == 0x02: # axis event
                axis = ((value + 32768) >> 8)
                # Axes 0,1 left stick X,Y
                if number == 0:
                    NSG.leftXAxis(axis)
                elif number == 1:
                    NSG.leftYAxis(axis)
                # Xbox throttle 0..255 but NS throttle is a button on/ff
                elif number == 2:
                    if axis > 128:
                        NSG.press(NSButton.LEFT_THROTTLE)
                    else:
                        NSG.release(NSButton.LEFT_THROTTLE)
                # Axes 3,4 right stick X,Y
                elif number == 3:
                    NSG.rightXAxis(axis)
                elif number == 4:
                    NSG.rightYAxis(axis)
                # Xbox throttle 0..255 but NS throttle is a button on/ff
                elif number == 5:
                    if axis > 128:
                        NSG.press(NSButton.RIGHT_THROTTLE)
                    else:
                        NSG.release(NSButton.RIGHT_THROTTLE)
                # Axes 6,7 directional pad X,Y
                elif number == 6:
                    NSG.dPadXAxis(axis)
                elif number == 7:
                    NSG.dPadYAxis(axis)

def read_ps4ds(jsdev):
    """
    The Sony Playstation 4 controller has fewer buttons. The throttles are
    analog (see axes) and binary (see buttons). Runs as a thread.

    axis    0: left stick X
            1: left stick Y
            2: left throttle
            3: right stick X
            4: right stick Y
            5: right throttle
            6: dPad X
            7: dPad Y

    button  0: cross            NS B
            1: circle           NS A
            2: triangle         NS X
            3: square           NS Y
            4: left trigger     NS left trigger
            5: right trigger    NS right trigger
            6: left throttle    NS left throttle
            7: right throttle   NS right throttle
            8: share            NS minus
            9: options          NS plus
           10: logo             NS home
           11: left stick button  NS left stick button
           12: right stick button NS rgith stick button


    share   options

            triangle
    square          circle
            cross
    """

    BUTTON_MAP = array.array('B', [
        NSButton.B,
        NSButton.A,
        NSButton.Y,
        NSButton.X,
        NSButton.LEFT_TRIGGER,
        NSButton.RIGHT_TRIGGER,
        NSButton.LEFT_THROTTLE,
        NSButton.RIGHT_THROTTLE,
        NSButton.MINUS,
        NSButton.PLUS,
        NSButton.HOME,
        NSButton.LEFT_STICK,
        NSButton.RIGHT_STICK])

    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                button_out = BUTTON_MAP[number]
                if value:
                    NSG.press(button_out)
                else:
                    NSG.release(button_out)

            if type == 0x02: # axis event
                axis = ((value + 32768) >> 8)
                # Axes 0,1 left stick X,Y
                if number == 0:
                    NSG.leftXAxis(axis)
                elif number == 1:
                    NSG.leftYAxis(axis)
                # axis 2 Xbox throttle 0..255 but NS throttle is a button on/ff
                # Axes 3,4 right stick X,Y
                elif number == 3:
                    NSG.rightXAxis(axis)
                elif number == 4:
                    NSG.rightYAxis(axis)
                # axis 5 Xbox throttle 0..255 but NS throttle is a button on/ff
                # Axes 6,7 directional pad X,Y
                elif number == 6:
                    NSG.dPadXAxis(axis)
                elif number == 7:
                    NSG.dPadYAxis(axis)

def read_dragon_rise(jsdev, right_side):
    """
    Map two Dragon Rise arcade joysticks to one NS gamepad
    The Dragon Rise arcade joystick has 1 stick and up to 10 buttons. Two are required
    to make 1 gamepad with 2 sticks plus 18 buttons. The right_side flag determines
    which joystick is the left or right side of the gamepad.
    """
    BUTTON_MAP_LEFT = array.array('B', [
        NSButton.LEFT_THROTTLE,
        NSButton.LEFT_TRIGGER,
        NSButton.MINUS,
        255,    # DPAD Up
        255,    # DPAD Right
        255,    # DPAD Down
        255,    # DPAD Left
        NSButton.LEFT_STICK,
        NSButton.CAPTURE,
        NSButton.CAPTURE,
        NSButton.CAPTURE,
        NSButton.CAPTURE])

    BUTTON_MAP_RIGHT = array.array('B', [
        NSButton.RIGHT_THROTTLE,
        NSButton.RIGHT_TRIGGER,
        NSButton.PLUS,
        NSButton.A,
        NSButton.B,
        NSButton.X,
        NSButton.Y,
        NSButton.RIGHT_STICK,
        NSButton.HOME,
        NSButton.HOME,
        NSButton.HOME,
        NSButton.HOME])

    dpad_bits = 0
    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                if right_side:
                    button_out = BUTTON_MAP_RIGHT[number]
                else:
                    button_out = BUTTON_MAP_LEFT[number]
                if button_out == 255:
                    if value:
                        dpad_bits |= (1 << (number - 3))
                    else:
                        dpad_bits &= ~(1 << (number - 3))
                    NSG.dPad(BUTTONS_MAP_DPAD[dpad_bits])
                else:
                    if value:
                        NSG.press(button_out)
                    else:
                        NSG.release(button_out)

            if type == 0x02: # axis event
                # NS wants values 0..128..255 where 128 is center position
                axis = ((value + 32768) >> 8)
                if right_side:
                    # Axes 0,1 right stick X,Y
                    if number == 0:
                        NSG.rightXAxis(axis)
                    elif number == 1:
                        NSG.rightYAxis(axis)
                else:
                    # Axes 0,1 left stick X,Y
                    if number == 0:
                        NSG.leftXAxis(axis)
                    elif number == 1:
                        NSG.leftYAxis(axis)

def read_le3dp(jsdev):
    """
    The Logitech Extreme 3D Pro joystick (also known as a flight stick)
    has a large X,Y,twist joystick with an 8-way hat switch on top.
    This maps the large X,Y axes to the gamepad right thumbstick and
    the hat switch to the gamepad left thumbstick. There are six
    buttons on the top of the stick and six on the base. The twist
    used to control the stick buttons. Each gamepad thumbstick is
    also a button. For example, clicking the right thumbstick enables
    stealth mode in Zelda:BOTW.
    Map LE3DP button numbers to NS gamepad buttons
    LE3DP buttons
    0 = front trigger
    1 = side thumb rest button
    2 = top large left
    3 = top large right
    4 = top small left
    5 = top small right

    Button array (2 rows, 3 columns) on base

    7 9 11
    6 8 10
    """
    BUTTON_MAP = array.array('B', [
        NSButton.A,             # Front trigger
        NSButton.B,             # Side thumb trigger
        NSButton.X,             # top large left
        NSButton.Y,             # top large right
        NSButton.LEFT_TRIGGER,  # top small left
        NSButton.RIGHT_TRIGGER, # top small right
        NSButton.MINUS,
        NSButton.PLUS,
        NSButton.CAPTURE,
        NSButton.HOME,
        NSButton.LEFT_THROTTLE,
        NSButton.RIGHT_THROTTLE])

    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                button_out = BUTTON_MAP[number]
                if value:
                    NSG.press(button_out)
                else:
                    NSG.release(button_out)

            if type == 0x02: # axis event
                axis = ((value + 32768) >> 8)
                # Axes 0,1 -> NS left thumbstick X,Y
                if number == 0:
                    NSG.leftXAxis(axis)
                elif number == 1:
                    NSG.leftYAxis(axis)
                # Axis 2 twist
                # Axis 3 throttle lever
                # Axes 4,5 hat switch -> NS right thumbstick X,Y
                elif number == 4:
                    NSG.rightXAxis(axis)
                elif number == 5:
                    NSG.rightYAxis(axis)

def read_t16k(jsdev):
    """
    Map T16K button numbers to NS gamepad buttons
    The Thrustmaster T.16000M ambidextrous joystick (also known as a flight stick)
    has a large X,Y,twist joystick with an 8-way hat switch on top.
    This function maps the large X,Y axes to the gamepad right thumbstick and
    the hat switch to the gamepad left thumbstick. There are four
    buttons on the top of the stick and 12 on the base. The twist
    used to control the stick buttons. Each gamepad thumbstick is
    also a button. For example, clicking the right thumbstick enables
    stealth mode in Zelda:BOTW.
    Map T16K button numbers to NS gamepad buttons
    T16K buttons
    0 = trigger
    1 = top center
    2 = top left
    3 = top right

    Button array on base, left side

    4
    9 5
      8 6
        7

    Button array on base, right side

          10
       11 15
    12 14
    13
    """
    BUTTON_MAP = array.array('B', [
        NSButton.A,             # Trigger
        NSButton.B,             # Top center
        NSButton.X,             # Top Left
        NSButton.Y,             # Top Right
        NSButton.LEFT_TRIGGER,  # Base left 4
        NSButton.RIGHT_TRIGGER, # Base left 5
        NSButton.MINUS,         # Base left 6
        NSButton.PLUS,          # Base left 7
        NSButton.CAPTURE,       # Base left 8
        NSButton.HOME,          # Base left 9
        NSButton.LEFT_THROTTLE, # Base right 10
        NSButton.RIGHT_THROTTLE,# Base right 11
        NSButton.LEFT_THROTTLE, # Base right 12
        NSButton.RIGHT_THROTTLE,# Base right 13
        NSButton.LEFT_THROTTLE, # Base right 14
        NSButton.RIGHT_THROTTLE])# Base right 15

    while True:
        try:
            evbuf = jsdev.read(8)
        except:
            jsdev.close()
            break
        if evbuf:
            timestamp, value, type, number = unpack('IhBB', evbuf)
            if type == 0x01: # button event
                button_out = BUTTON_MAP[number]
                if value:
                    NSG.press(button_out)
                else:
                    NSG.release(button_out)

            if type == 0x02: # axis event
                # NS wants values 0..128..255 where 128 is center position
                axis = ((value + 32768) >> 8)
                # Axes 0,1 -> NS left thumbstick X,Y
                if number == 0:
                    NSG.leftXAxis(axis)
                elif number == 1:
                    NSG.leftYAxis(axis)
                # Axis 2 twist
                # Axis 3 throttle lever
                # Axes 4,5 hat switch -> right thumbstick X,Y
                elif number == 4:
                    NSG.rightXAxis(axis)
                elif number == 5:
                    NSG.rightYAxis(axis)

class GPIO_NS_Button:
    """ Assign NS button to GPIO pin """
    def __init__(self, gpio_number, ns_button):
        self.ns_button = ns_button
        self.gpio_number = gpio_number
        self.button = Button(gpio_number)
        self.pressed = self.button.is_pressed
        self.rose_state = False
        self.fell_state = False

    def fell(self):
        """ Return True if button was pressed else return False """
        if self.fell_state:
            self.fell_state = False
            return True
        return False

    def rose(self):
        """ Return True if button was released else return False """
        if self.rose_state:
            self.rose_state = False
            return True
        return False

    def update(self):
        """
        Update button rose/fell state.
        This tracks button transitions rather than the current state.
        """
        if self.button.is_pressed:
            if not self.pressed:
                self.fell_state = True
            self.pressed = True
        else:
            if self.pressed:
                self.rose_state = True
            self.pressed = False


class GPIO_NS_DPad:
    """ Assign NS direction pad to GPIO pins """
    def __init__(self, gpio_up, gpio_right, gpio_down, gpio_left):
        self.dpad_bits = 0
        self.buttonup = Button(gpio_up)
        self.buttonup.when_pressed = self.press_up
        self.buttonup.when_released = self.release_up

        self.buttonright = Button(gpio_right)
        self.buttonright.when_pressed = self.press_right
        self.buttonright.when_released = self.release_right

        self.buttondown = Button(gpio_down)
        self.buttondown.when_pressed = self.press_down
        self.buttondown.when_released = self.release_down

        self.buttonleft = Button(gpio_left)
        self.buttonleft.when_pressed = self.press_left
        self.buttonleft.when_released = self.release_left

    def press_up(self):
        """ dPad Up button pressed so update NS gadget dPad """
        self.dpad_bits |= 1
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def release_up(self):
        """ dPad Up button released so update NS gadget dPad """
        self.dpad_bits &= ~1
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def press_right(self):
        """ dPad Right button pressed so update NS gadget dPad """
        self.dpad_bits |= (1 << 1)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def release_right(self):
        """ dPad Right button released so update NS gadget dPad """
        self.dpad_bits &= ~(1 << 1)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def press_down(self):
        """ dPad Down button pressed so update NS gadget dPad """
        self.dpad_bits |= (1 << 2)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def release_down(self):
        """ dPad Down button released so update NS gadget dPad """
        self.dpad_bits &= ~(1 << 2)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def press_left(self):
        """ dPad Left button pressed so update NS gadget dPad """
        self.dpad_bits |= (1 << 3)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

    def release_left(self):
        """ dPad Left button released so update NS gadget dPad """
        self.dpad_bits &= ~(1 << 3)
        NSG.dPad(BUTTONS_MAP_DPAD[self.dpad_bits])

def gpio_handler():
    """ Map Raspberry Pi GPIO pins to NS buttons """
    all_buttons = list()
    # Left side (blue joy-con) buttons
    all_buttons.append(GPIO_NS_Button(4, NSButton.LEFT_THROTTLE))
    all_buttons.append(GPIO_NS_Button(17, NSButton.LEFT_TRIGGER))
    all_buttons.append(GPIO_NS_Button(27, NSButton.MINUS))
    all_buttons.append(GPIO_NS_Button(22, NSButton.CAPTURE))
    GPIO_NS_DPad(5, 6, 13, 19)
    all_buttons.append(GPIO_NS_Button(26, NSButton.LEFT_STICK))

    # Right side (red joy-con) buttons
    all_buttons.append(GPIO_NS_Button(23, NSButton.RIGHT_THROTTLE))
    all_buttons.append(GPIO_NS_Button(24, NSButton.RIGHT_TRIGGER))
    all_buttons.append(GPIO_NS_Button(25, NSButton.PLUS))
    all_buttons.append(GPIO_NS_Button(8, NSButton.HOME))
    all_buttons.append(GPIO_NS_Button(7, NSButton.A))
    all_buttons.append(GPIO_NS_Button(12, NSButton.B))
    all_buttons.append(GPIO_NS_Button(16, NSButton.X))
    all_buttons.append(GPIO_NS_Button(20, NSButton.Y))
    all_buttons.append(GPIO_NS_Button(21, NSButton.RIGHT_STICK))

    while True:
        for button in all_buttons:
            button.update()
            if button.fell():
                NSG.press(button.ns_button)
            if button.rose():
                NSG.release(button.ns_button)
            time.sleep(0.005)

def read_midi_notes(midi_input_name, first_note):
    """
    Read MIDI note on/off and generate NS gamepad events.
    first_note -- First/lowest MIDI note number on keyboard
    """
    NOTE_MAP = [
        # Honk horn
        {'buttons': [NSButton.RIGHT_TRIGGER, NSButton.B]},    # Note On 53
        # Radio on/off
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.RIGHT_TRIGGER], 'dpad': NSDPad.UP},    # Note On 54
        0,                  # Note On 55
        # Radio prev station/if radio off, left turn signal
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.RIGHT_TRIGGER], 'dpad': NSDPad.LEFT}, # Note On 56
        0,                  # Note On 57
        # Radio nextious station/if radio off, right turn signal
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.RIGHT_TRIGGER], 'dpad': NSDPad.RIGHT},  # Note On 58
        0,                  # Note On 59
        0,                  # Note On 60
        0,                  # Note On 61
        0,                  # Note On 62
        0,                  # Note On 63
        0,                  # Note On 64
        0,                  # Note On 65
        0,                  # Note On 66
        0,                  # Note On 67
        0,                  # Note On 68
        0,                  # Note On 69
        0,                  # Note On 70
        0,                  # Note On 71
        0,                  # Note On 72
        0,                  # Note On 73
        0,                  # Note On 74
        # Unload
        {'buttons': [NSButton.RIGHT_TRIGGER, NSButton.X]},   # Note On 75
        # Open cover
        {'buttons': [NSButton.LEFT_TRIGGER], 'dpad': NSDPad.LEFT},   # Note On 76
        # Tool on/off
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.Y]},   # Note On 77
        # Head lights
        {'buttons': [NSButton.RIGHT_TRIGGER, NSButton.A]},  # Note On 78
        # OK, next
        {'buttons': [NSButton.A]},  # Note On 79
        # Fold/unfold tool
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.B]},   # Note On 80
        # Jump, attach/detach tool
        {'buttons': [NSButton.B]},  # Note On 81
        # Raise/lower tool
        {'buttons': [NSButton.LEFT_TRIGGER, NSButton.A]},   # Note On 82
        # Crouch, select tool
        {'buttons': [NSButton.X]},  # Note On 83
        # Enter/exit
        {'buttons': [NSButton.Y]},  # Note On 84
    ]

    with mido.open_input(midi_input_name) as inport:
        for msg in inport:
            if msg.type == 'note_on':
                index = msg.note - first_note
                print(index)
                if index >= 0 and NOTE_MAP[index]:
                    controls = NOTE_MAP[index]
                    print(controls)
                    if 'buttons' in controls:
                        for btn in controls['buttons']:
                            print('press ', btn)
                            NSG.press(btn)
                    if 'dpad' in controls:
                        print('dpad ', controls['dpad'])
                        NSG.dPad(controls['dpad'])
            elif msg.type == 'note_off':
                index = msg.note - first_note
                if index >= 0 and NOTE_MAP[index]:
                    controls = NOTE_MAP[index]
                    if 'dpad' in controls:
                        print('dpad centered')
                        NSG.dPad(NSDPad.CENTERED)
                    if 'buttons' in controls:
                        for btn in reversed(controls['buttons']):
                            print('release ', btn)
                            NSG.release(btn)

def main():
    """ joystick ioctl code based on https://gist.github.com/rdb/8864666 """
    threading.Thread(target=gpio_handler, args=(), daemon=True).start()

    # Look for new MIDI input devices
    for midi_input_name in mido.get_input_names():
        if 'AKM320' in midi_input_name:
            print(midi_input_name)
            thr_id = threading.Thread(target=read_midi_notes, args=(midi_input_name, 53,), daemon=True)
            thr_id.start()

    dr_count = 0
    joysticks = {}
    joysticks_to_del = list()
    while True:
        # For all known joysticks make sure its thread is still alive. If not, forget the joystick
        # The thread ends when the joystick is unplugged.
        for jsname in joysticks:
            if not joysticks[jsname].is_alive():
                print("joystick %s removed" % jsname)
                joysticks_to_del.append(jsname)
        for jsname in joysticks_to_del:
            del joysticks[jsname]
        joysticks_to_del.clear()
        # Look for new joysticks
        # For all joysticks in /dev/input/ and not do not have a thread, start a thread
        # Each thread reads from its associated joystick and writes to the NS gadget device.
        for fn in os.listdir('/dev/input'):
            if fn.startswith('js'):
                jsname = '/dev/input/' + fn
                if not jsname in joysticks:
                    try:
                        jsdev = open(jsname, 'rb')
                    except:
                        break
                    buf = array.array('B', [0] * 64)
                    ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
                    jslongname = buf.tobytes().rstrip(b'\x00').decode('utf-8').upper()
                    if 'HORIPAD' in jslongname:
                        print("Found HoriPad")
                        thr_id = threading.Thread(target=read_horipad, args=(jsdev,), daemon=True)
                        thr_id.start()
                        joysticks[jsname] = thr_id
                    elif 'DRAGONRISE INC.' in jslongname:
                        print("Found Dragon Rise")
                        # At least 2 DR arcade joysticks are required to make a gamepad.
                        if dr_count & 1:
                            thr_id = threading.Thread(target=read_dragon_rise, args=(jsdev, True,), daemon=True)
                            thr_id.start()
                        else:
                            thr_id = threading.Thread(target=read_dragon_rise, args=(jsdev, False,), daemon=True)
                            thr_id.start()
                        dr_count += 1
                        joysticks[jsname] = thr_id
                    elif 'LOGITECH EXTREME 3D' in jslongname:
                        print("Found Logitech Extreme 3D Pro")
                        thr_id = threading.Thread(target=read_le3dp, args=(jsdev,), daemon=True)
                        thr_id.start()
                        joysticks[jsname] = thr_id
                    elif 'THRUSTMASTER T.16000M' in jslongname:
                        print("Found Thrustmaster T.16000M")
                        thr_id = threading.Thread(target=read_t16k, args=(jsdev,), daemon=True)
                        thr_id.start()
                        joysticks[jsname] = thr_id
                    elif 'MICROSOFT X-BOX ONE' in jslongname:
                        print("Found Xbox One")
                        thr_id = threading.Thread(target=read_xbox1, args=(jsdev,), daemon=True)
                        thr_id.start()
                        joysticks[jsname] = thr_id
                    elif 'SONY INTERACTIVE ENTERTAINMENT WIRELESS CONTROLLER' in jslongname:
                        print("Found Sony PS4DS")
                        thr_id = threading.Thread(target=read_ps4ds, args=(jsdev,), daemon=True)
                        thr_id.start()
                        joysticks[jsname] = thr_id
                    else:
                        jsdev.close()
        time.sleep(0.1)

if __name__ == "__main__":
    main()
