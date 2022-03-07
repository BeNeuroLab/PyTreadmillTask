from pyControl.hardware import *
from pyb import UART
from machine import Timer

class USB_UART():
    def __init__(self, name):
        self.uart = UART(1, 9600)                         # init with given baudrate
        self.uart.init(9600, bits=8, parity=None, stop=1) # init with given parameters
        # self.timer = Timer(3)
        # self.timer.init(mode=Timer.PERIODIC)
        # self.timer_ch = self.timer.channel(Timer.A, freq=5)
        # self.timer_ch.irq(handler=self._timer_ISR, trigger=Timer.TIMEOUT)
        self.buffer = bytearray(25)
        self.name = name
        assign_ID(self)
        # Data acqisition variables
        self.timer = pyb.Timer(available_timers.pop())
        self.timestamp = fw.current_time

    def _timer_ISR(self, t):
        self.uart.readinto(self.buffer)
        self.timestamp = fw.current_time
        interrupt_queue.put(self.ID)
    
    def start_test(self):
        self.timer.init(freq=self.sampling_rate)
        self.timer.callback(self._timer_ISR)