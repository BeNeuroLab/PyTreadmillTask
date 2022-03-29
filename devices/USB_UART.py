from pyControl.hardware import *
from pyb import UART
from machine import Timer


class USB_UART(IO_object):
    def __init__(self, name):
        self.uart = UART(1, 9600)                         # init with given baudrate
        self.uart.init(9600, bits=8, parity=None, stop=1) # init with given parameters
        self.buffer = bytearray(8)
        self.name = name
        assign_ID(self)
        # Data acqisition variables
        self.timer = pyb.Timer(available_timers.pop())
        self.timestamp = fw.current_time
        self.freq = -1
        self.prev_freq = -1

    def _timer_ISR(self, t):
        if self.uart.any() > 0:    # no message
            self.uart.readinto(self.buffer, 2)
            self.freq = int.from_bytes(self.buffer, 'little')
            if self.freq != self.prev_freq:
                self.prev_freq = self.freq
                self.timestamp = fw.current_time
                interrupt_queue.put(self.ID)
       
    def _initialise(self):
        self.timer.init(freq=1000)   # this should be 2*(client frequency)
        self.timer.callback(self._timer_ISR)
    
    def _process_interrupt(self):
        fw.event_queue.put((self.timestamp, fw.event_typ, fw.events[self.name]))
        