from pyControl.utility import *
import hardware_definition as hw

states = ['init']
events = ['read']
initial_state = 'init'

# def run_start():
#     print('run_start()')

# def run_end():
#     hw.off()
#     print('run_end()')

hw.usb_uart.start_test()

def init(event):
    if event == 'entry':
        print('entering init')
    elif event == 'exit':
        print('exiting init')
    elif event == 'read':
        # for i in range(len(hw.usb_uart.buffer)):
        print(hw.usb_uart.output)
    