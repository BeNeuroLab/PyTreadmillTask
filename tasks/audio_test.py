from pyControl.utility import *
import hardware_definition as hw

states = ['init']
events = []
initial_state = 'init'

# def run_start():
#     print('run_start()')

# def run_end():
#     hw.off()
#     print('run_end()')

def init(event):
    hw.usb_uart.start_testing()
    if event == 'entry':
        print('entering init')
    elif event == 'exit':
        print('exiting init')
    elif event == 'read':
        print(hw.usb_uart.buffer)
    