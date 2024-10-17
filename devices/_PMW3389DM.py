import utime, machine, math, gc
from array import array
from pyControl.hardware import *
from devices.PMW3389DM_srom_0x04 import PROGMEM


def twos_comp(val, bits=16):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)         # compute negative value
    return val                          # return positive value as is


class PMW3389DM():
    """ mouse motion sensor."""
    def __init__(self,
                 SPI_type: str,
                 reset: str = None,
                 CS: str = None,
                 MI: str = None,
                 MO: str = None,
                 SCK: str = None):

        # SPI_type = 'SPI1' or 'SPI2' or 'softSPI'
        SPIparams = {'baudrate': 1000000, 'polarity': 1, 'phase': 1,
                     'bits': 8, 'firstbit': machine.SPI.MSB}
        if '1' in SPI_type:
            self.SPI = machine.SPI(1, **SPIparams)

        elif '2' in SPI_type:
            self.SPI = machine.SPI(2, **SPIparams)

        elif 'soft' in SPI_type.lower():  # Works for newer versions of micropython
            self.SPI = machine.SoftSPI(sck=machine.Pin(SCK, mode=machine.Pin.OUT, pull=machine.Pin.PULL_DOWN),
                                       mosi=machine.Pin(MO, mode=machine.Pin.OUT, pull=machine.Pin.PULL_DOWN),
                                       miso=machine.Pin(MI, mode=machine.Pin.IN),
                                       **SPIparams
                                       )

        self.select = Digital_output(pin=CS, inverted=True)
        self.reset = Digital_output(pin=reset, inverted=True)
        
        self.reset.off()
        self.select.off()

    def read_pos(self):
        # write and read Motion register to lock the content of delta registers
        self.write_register(0x02, 0x01)
        self.read_register(0x02)

        delta_x_L = self.read_register(0x03)
        delta_x_H = self.read_register(0x04)
        delta_y_L = self.read_register(0x05)
        delta_y_H = self.read_register(0x06)

        delta_x = delta_x_H + delta_x_L
        delta_y = delta_y_H + delta_y_L

        delta_x = int.from_bytes(delta_x, 'little')
        delta_y = int.from_bytes(delta_y, 'little')

        delta_x = twos_comp(delta_x)
        delta_y = twos_comp(delta_y)

        return delta_x, delta_y

    def read_register(self, addrs: int):
        """
        addrs < 128
        """
        # ensure MSB=0
        addrs = addrs & 0x7f
        addrs = addrs.to_bytes(1, 'little')
        self.select.on()
        self.SPI.write(addrs)
        utime.sleep_us(100)  # tSRAD
        data = self.SPI.read(1)
        utime.sleep_us(1)  # tSCLK-NCS for read operation is 120ns
        self.select.off()
        utime.sleep_us(19)  # tSRW/tSRR (=20us) minus tSCLK-NCS
        return data

    def write_register(self, addrs: int, data: int):
        """
        addrs < 128
        """
        # flip the MSB to 1:
        addrs = addrs | 0x80
        addrs = addrs.to_bytes(1, 'little')
        data = data.to_bytes(1, 'little')
        self.select.on()
        self.SPI.write(addrs)
        self.SPI.write(data)
        utime.sleep_us(20)  # tSCLK-NCS for write operation
        self.select.off()
        utime.sleep_us(100)  # tSWW/tSWR (=120us) minus tSCLK-NCS. Could be shortened, but is looks like a safe lower bound

    def power_up(self):
        """
        Perform the power up sequence
        As per page 26 of datasheet
        """
        # 2
        self.select.off()
        self.select.on()
        self.select.off()
        # 3
        self.write_register(0x3a, 0x5a)
        # 4
        utime.sleep_ms(50)
        # 5
        self.read_pos()

        # SROM Download
        # As per page 23 of datasheet
        # 2
        self.write_register(0x10, 0x20)
        # 3
        self.write_register(0x13, 0x1d)
        # 4
        utime.sleep_ms(10)
        # 5
        self.write_register(0x13, 0x18)
        # 6
        self.download_srom(PROGMEM)
        # 7
        ID = int.from_bytes(self.read_register(0x2a), 'little')
        assert ID == 0x04, "bad SROM v={}".format(ID)
        # 8
        # Write 0x00 to Config2 register for wired mouse or 0x20 for wireless mouse design (Enable/Disable Rest mode)
        self.write_register(0x10, 0x00)

        # CONFIGURATION
        # set initial CPI resolution
        self.write_register(0x0f, 0x00)  # CPI setting 0x31=5000; 0x00=100
        # set lift detection
        self.write_register(0x63, 0x03)  # Lift detection: +3mm
        self.CPI = int.from_bytes(self.read_register(0x0f), 'little') * 100 + 100

        self.select.off()

        utime.sleep_ms(10)

    def shut_down(self, deinitSPI=True):
        """
        Perform the shut down sequence
        As per page 27 of datasheet
        """
        self.select.off()
        utime.sleep_ms(1)
        self.select.on()
        utime.sleep_ms(1)
        self.reset.on()
        utime.sleep_ms(60)
        self.read_pos()
        utime.sleep_ms(1)
        self.select.off()
        utime.sleep_ms(1)
        if deinitSPI:
            self.SPI.deinit()

    def download_srom(self, srom):
        self.select.on()
        # flip the MSB to 1:
        self.SPI.write((0x62 | 0x80) .to_bytes(1, 'little'))
        utime.sleep_us(15)
        for srom_byte in srom:
            self.SPI.write(srom_byte.to_bytes(1, 'little'))
            utime.sleep_us(15)

        self.select.off()
        utime.sleep_ms(1)

    def read_register_buff(self, addrs: bytes, buff: bytes):
        """
        addrs < 128
        """
        self.select.on()
        self.SPI.write(addrs)
        utime.sleep_us(100)  # tSRAD
        self.SPI.readinto(buff)
        utime.sleep_us(1)  # tSCLK-NCS for read operation is 120ns
        self.select.off()
        utime.sleep_us(19)  # tSRW/tSRR (=20us) minus tSCLK-NCS

    def write_register_buff(self, addrs: bytes, data: bytes):
        """
        addrs < 128
        """
        # flip the MSB to 1:...
        self.select.on()
        self.SPI.write(addrs)
        self.SPI.write(data)
        utime.sleep_us(20)  # tSCLK-NCS for write operation
        self.select.off()
        utime.sleep_us(100)  # tSWW/tSWR (=120us) minus tSCLK-NCS. Could be shortened, but is looks like a safe lower bound


class MotionDetector(Analog_input):
    """
    Using the Analog_input code to interface with 2 PMW3389DM sensors
    reading `x` (SPI2) and `y` (softSPI) separately.
    """
    def __init__(self, reset, cs1, cs2,
                 name='MotDet', calib_coef=1,
                 threshold=1, sampling_rate=100, event='motion'):
        """
        name: name of the analog signal which will be streamed to the PC
        cs1, cs2: Chip select pins for each sensor
        threshold: in centimeters,
                   distance travelled longer than THRESHOLD triggers a PyControl event,
        under the hood, THRESHOLD is saved as the square of the movement counts.
        """
        self.sensor_x = PMW3389DM(SPI_type='SPI2', reset=reset, CS=cs1)
        self.sensor_y = PMW3389DM(SPI_type='SPI2', reset=reset, CS=cs2)

        self.sensor_x.power_up()
        self.sensor_y.power_up()
        self.calib_coef = calib_coef
        self.threshold = threshold

        # Motion sensor variables
        self.x_buffer = bytearray(2)
        self.y_buffer = bytearray(2)
        self.x_buffer_mv = memoryview(self.x_buffer)
        self.y_buffer_mv = memoryview(self.y_buffer)
        self.delta_x_l = self.x_buffer_mv[0:1]
        self.delta_x_h = self.x_buffer_mv[1:]
        self.delta_y_l = self.y_buffer_mv[0:1]
        self.delta_y_h = self.y_buffer_mv[1:]

        self.delta_x, self.delta_y = 0, 0
        self._delta_x, self._delta_y = 0, 0
        self.x, self.y = 0, 0  # to be accessed from the task, unit=movement count in CPI*inches

        # Parent
        Analog_input.__init__(self, pin=None, name=name + '-X', sampling_rate=int(sampling_rate),
                              threshold=threshold, rising_event=event, falling_event=None,
                              data_type='l')
        self.data_chx = self.data_channel
        self.data_chy = Data_channel(name + '-Y', sampling_rate, data_type='l')
        self.crossing_direction = True  # to conform to the Analog_input syntax
        self.timestamp = fw.current_time
        self.acquiring = False

        gc.collect()
        utime.sleep_ms(2)

    @property
    def threshold(self):
        "return the value in cms"
        return math.sqrt(self._threshold) / self.sensor_x.CPI * 2.54

    @threshold.setter
    def threshold(self, new_threshold):
        self._threshold = int((new_threshold / 2.54 * self.sensor_x.CPI)**2) * self.calib_coef
        self.reset_delta()

    def reset_delta(self):
        "reset the accumulated position data"
        self.delta_x, self.delta_y = 0, 0

    def read_sample(self):
        "read the sensors once"
        self.sensor_y.write_register_buff(b'\x82', b'\x01')
        self.sensor_y.read_register_buff(b'\x02', self.delta_y_l)
        self.sensor_y.read_register_buff(b'\x03', self.delta_y_l)
        self.sensor_y.read_register_buff(b'\x04', self.delta_y_l)
        self.sensor_y.read_register_buff(b'\x05', self.delta_y_l)
        self.sensor_y.read_register_buff(b'\x06', self.delta_y_h)
        self._delta_y = twos_comp(int.from_bytes(self.y_buffer_mv, 'little'))

        self.sensor_x.write_register_buff(b'\x82', b'\x01')
        self.sensor_x.read_register_buff(b'\x02', self.delta_x_l)
        self.sensor_x.read_register_buff(b'\x03', self.delta_x_l)
        self.sensor_x.read_register_buff(b'\x04', self.delta_x_h)
        self.sensor_x.read_register_buff(b'\x05', self.delta_y_l)
        self.sensor_x.read_register_buff(b'\x06', self.delta_y_l)
        self._delta_x = twos_comp(int.from_bytes(self.x_buffer_mv, 'little'))

        self.delta_y += self._delta_y
        self.delta_x += self._delta_x

    def _timer_ISR(self, t):
        "Read a sample to the buffer, update write index."
        self.read_sample()
        self.data_chx.put(self._delta_x)
        self.data_chy.put(self._delta_y)

        if self.delta_x**2 + self.delta_y**2 >= self._threshold:
            self.x = self.delta_x
            self.y = self.delta_y
            self.reset_delta()
            self.timestamp = fw.current_time
            interrupt_queue.put(self.ID)

    def _stop_acquisition(self):
        # Stop sampling analog input values.
        self.timer.deinit()
        self.data_chx.stop()
        self.data_chy.stop()
        self.sensor_x.shut_down(deinitSPI=False)
        self.sensor_y.shut_down()
        self.acquiring = False

    def _start_acquisition(self):
        # Start sampling analog input values.
        self.timer.init(freq=self.data_chx.sampling_rate)
        self.timer.callback(self._timer_ISR)
        self.acquiring = True

    def record(self):
        "Start streaming data to computer."
        self.data_chx.record()
        self.data_chy.record()
        if not self.acquiring:
            self._start_acquisition()
