
   
from pyControl.utility import *
import hardware_definition as hw
from pyb import UART
import time

states = ['init']
events = ['audio_freq']
initial_state = 'init'

uart = UART(1, 9600)                         # init with given baudrate
uart.init(9600, bits=8, parity=None, stop=1, timeout=0)

pin = hw.Digital_output(pin='W74', inverted=True)

i = 0

buffer = bytearray(8)

# hw.usb_uart._initialise()
def init(event):
    global i
    if event == 'entry':
        print('entering init')
        '''
        while True:         
            if uart.any() > 0:
                uart.readinto(buffer, 2)
                output = int.from_bytes(buffer, 'little')
                # uart.write((1).to_bytes(2, 'little'))
                # i = (i + 1) % 10
            # uart.readinto(buffer, 2)
            # output = int.from_bytes(buffer, 'little')
            # uart.write((1).to_bytes(2, 'little'))
        '''
        
    elif event == 'exit':
        print('exiting init')
    elif event == 'audio_freq':
        # for i in range(len(hw.usb_uart.buffer)):
        if hw.usb_uart.freq == 1:
            pin.on()
        if hw.usb_uart.freq == 0:
            pin.off()
        
        print(hw.usb_uart.freq)
        print(hw.usb_uart.prev_freq)