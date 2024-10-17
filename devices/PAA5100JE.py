import time, gc, math, machine
from array import array
from pyControl.hardware import *
from devices.PAA5100JE_firmware import *

def to_signed_16(value):
    """Convert a 16-bit integer to a signed 16-bit integer."""
    if value & 0x8000:  # Check if the sign bit is set
        value -= 0x10000  # Convert to negative
    return value

class PAA5100JE():
    """
    Optical tracking sensor:
    C++ code reference can be found on: https://github.com/pimoroni/pimoroni-pico.git
    and on https://github.com/zic-95/PAA5100JE/blob/main/src/PAA5100JE.cpp
    """
    def __init__(self, 
                 SPI_type: str, 
                 CS: str, 
                 MI: str = None, 
                 MO: str = None, 
                 SCK: str = None):
                     
        # Initialize SPI
        # SPI_type = 'SPI1' or 'SPI2' or 'softSPI'
        SPIparams = {'baudrate': 1000000, 'polarity': 1, 'phase': 1,
                     'bits': 8, 'firstbit': machine.SPI.MSB}
        
        if '1' in SPI_type:
            self.spi = machine.SPI(1, **SPIparams)

        elif '2' in SPI_type:
            self.spi = machine.SPI(2, **SPIparams)

        elif 'soft' in SPI_type.lower():  # Works for newer versions of micropython
            self.spi = machine.SoftSPI(sck=machine.Pin(SCK, mode=machine.Pin.OUT, pull=machine.Pin.PULL_DOWN),
                                       mosi=machine.Pin(MO, mode=machine.Pin.OUT, pull=machine.Pin.PULL_DOWN),
                                       miso=machine.Pin(MI, mode=machine.Pin.IN),
                                       **SPIparams
                                       )
                         
        # Define Chip Select (CS) pin (active low)
        self.select = Digital_output(pin=CS, inverted=True)

        time.sleep_ms(1)
        self.select.off() # Deselect the device by setting CS high
        time.sleep_ms(1)
        self.select.on() # Select the device by setting CS low
        time.sleep_ms(1)
        self.select.off()
        time.sleep_ms(1)
                     
        # Reset the sensor
        self.firmware = PAA5100JE_firmware()
        self._write(self.firmware.REG_POWER_UP_RESET, 0x5A)

        time.sleep_ms(20)
        # Read motion registers once after reset
        for offset in range(5):
            self._read(self.firmware.REG_DATA_READY + offset)
        time.sleep_ms(1)
                           
        # Registers initialization protocol
        PROGMEM = self.firmware.init_registers()
        self._bulk_write(PROGMEM[0:10])
        res = self._read(0x67) & 0x80
        if res == 0x80:
            self._write(0x48, 0x04)
        else:
            self._write(0x48, 0x02)
        self._bulk_write(PROGMEM[10:20])
        
        if self._read(0x73) == 0x00:
            c1 = int(self._read(0x70))
            c2 = int(self._read(0x71))
            if c1 <= 28:
                c1 += 14
            if c1 > 28:
                c1 += 11
            c1 = max(0, min(0x3F, c1))
            c2 = (c2 * 45) // 100
    
            self._bulk_write([
                0x7F, 0x00,
                0x61, 0xAD,
                0x51, 0x70,
                0x7F, 0x0E
            ])
            self._write(0x70, c1)
            self._write(0x71, c2)

        self._bulk_write(PROGMEM[20:154])
        time.sleep_ms(10)
        self._bulk_write(PROGMEM[154:186])
        time.sleep_ms(10)
        self._bulk_write(PROGMEM[186:])
        
        time.sleep_ms(10)
        # Check for successful initialization
        prod_ID = self._read(0x00)
        assert prod_ID == 0x49
                     
    def set_rotation(self, degrees:int =0):
        """Set orientation of PAA5100 in increments of 90 degrees."""
        if degrees == 0:
            self.set_orientation(invert_x=True, invert_y=True, swap_xy=True)
        elif degrees == 90:
            self.set_orientation(invert_x=False, invert_y=True, swap_xy=False)
        elif degrees == 180:
            self.set_orientation(invert_x=False, invert_y=False, swap_xy=True)
        elif degrees == 270:
            self.set_orientation(invert_x=True, invert_y=False, swap_xy=False)
        else:
            raise TypeError("Degrees must be one of 0, 90, 180 or 270")

    def set_orientation(self, invert_x:bool =True, invert_y:bool =True, swap_xy:bool =True):
        """Set orientation of PAA5100 manually."""
        value = 0
        if swap_xy:
            value |= 0b10000000
        if invert_y:
            value |= 0b01000000
        if invert_x:
            value |= 0b00100000
        self._write(self.firmware.REG_ORIENTATION, value)
    
    def _write(self, address: int, value: int):
        """Write value into register"""
        address |= 0x80  # Flip MSB to 1
        address = address.to_bytes(1, 'little')  # Convert the address from integer to a single byte
        value = value.to_bytes(1, 'little')    # Convert the value from integer to a single byte
        
        self.select.on()
        time.sleep_us(1)
        self.spi.write(address)   # find specific address of the device
        self.spi.write(value)   # write value into the above address of the device
        time.sleep_us(5)  # tSWW
        self.select.off()
        time.sleep_us(5) # buffer time
   
    def _read(self, address: int):
        """Read register"""
        # Create a buffer to send
        address &= ~0x80  # Ensure MSB is 0
        address = address.to_bytes(1, 'little')  # Convert the integer to a single byte
        
        self.select.on()
        time.sleep_us(1)
        self.spi.write(address)
        time.sleep_us(5)  # tSRAD + tSWR
        
        data = self.spi.read(1)
        
        val = int.from_bytes(data, 'little')  # converts received data back to integer for further calculations
        time.sleep_us(1)  # tSCLK-NCS for read operation is 120ns
        self.select.off()
        time.sleep_us(5)  # tSRW/tSRR minus tSCLK-NCS
        return val

    def _bulk_write(self, data: int):
        """Write a list of commands into registers"""
        for x in range(0, len(data), 2):
            address, value = data[x : x + 2]
            self._write(address, value)
            
    def read_registers(self, address: int, buf: bytearray, len: int):
        """Read an array of data from the registers, used for reading motion burst"""
        address &= ~0x80  # Flip MSB to 1
        address = address.to_bytes(1, 'little')  # Convert the address from integer to a single byte
        
        self.select.on()
        time.sleep_us(1)
        self.spi.write(address)
        time.sleep_us(5)
        # Read 12 bytes of data from the motion burst register
        for i in range(12):
            buf[i] = self.spi.read(1)
        time.sleep_us(5)
        self.select.off()
        time.sleep_us(50)
        # Check for data being successfully read into the buffer
        assert buf[10] == 0x1F, str(buf[10])

    def shut_down(self, deinitSPI:bool =True):
        """Shutdown the sensor"""
        self.select.off()
        time.sleep_ms(1)
        self.select.on()
        time.sleep_ms(60)
        self._write(self.firmware.REG_SHUTDOWN, 0xB6)
        time.sleep_ms(1)
        self.select.off()
        time.sleep_ms(1)
        if deinitSPI:
            self.spi.deinit()
        
class MotionDetector2(Analog_input):
    """
    Using the Analog_input code to interface with 2 PAA5100JE sensors
    reading `x` (SPI2) and `y` (softSPI) separately.
    """
    def __init__(self, reset: str, cs1: str, cs2: str,
                 name='MotSen', threshold=1, calib_coef=1,  
                 sampling_rate=100, event='motion'):
        
        # Create SPI objects
        self.motSen_x = PAA5100JE('SPI2', cs1)
        self.motSen_y = PAA5100JE('SPI2', cs2)

        self.calib_coef = calib_coef
        self.threshold = threshold
        
        # Motion sensor variables
        self.x_buffer = bytearray(12)
        self.y_buffer = bytearray(12)
        self.x_buffer_mv = memoryview(self.x_buffer)
        self.y_buffer_mv = memoryview(self.y_buffer)
                     
        self.delta_x, self.delta_y = 0, 0    # accumulated position
        self._delta_x, self._delta_y = 0, 0  # instantaneous position
        self.x, self.y = 0, 0  # to be accessed from the task, unit=mm
        
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
        time.sleep_ms(2)
    
    @property
    def threshold(self):
        "return the value in mms"
        return math.sqrt(self._threshold)

    @threshold.setter
    def threshold(self, new_threshold):
        self._threshold = int((new_threshold)**2) * self.calib_coef
        self.reset_delta()
        
    def reset_delta(self):
        """reset the accumulated position data"""
        self.delta_x, self.delta_y = 0, 0
    
    def read_sample(self):
        """read motion once"""
        # All units are in millimeters
        # Read motion in x direction
        self.motSen_x.read_registers(self.firmware.REG_MOTION_BURST, self.x_buffer_mv, 12)
        self._delta_x = to_signed_16((self.x_buffer_mv[3] << 8) | self.x_buffer_mv[2])

        # Read motion in y direction
        self.motSen_y.read_registers(self.firmware.REG_MOTION_BURST, self.y_buffer_mv, 12)
        self._delta_y = to_signed_16((self.y_buffer_mv[5] << 8) | self.y_buffer_mv[4])
        
        # Record accumulated motion
        self.delta_y += self._delta_y
        self.delta_x += self._delta_x
        
    def _timer_ISR(self, t):
        """Read a sample to the buffer, update write index."""
        self.read_sample()
        self.data_chx.put(self._delta_x)
        self.data_chy.put(self._delta_y)

        if self.delta_x**2 + self.delta_y**2 >= self._threshold:
            self.x = self.delta_x
            self.y = self.delta_y
            self.reset_delta()
            self.timestamp = fw.current_time
            interrupt_queue.put(self.ID)  # Note: no self.ID for this sensor, cannot interrupt queue so data were not sent

    def _stop_acquisition(self):
        """Stop sampling analog input values."""
        self.timer.deinit()
        self.data_chx.stop()
        self.data_chy.stop()
        self.motSen_x.shut_down(deinitSPI=False)      
        self.motSen_y.shut_down()
        self.acquiring = False
        self.reset_delta()
        
    def _start_acquisition(self):
        """Start sampling analog input values"""
        self.timer.init(freq=self.data_chx.sampling_rate)
        self.timer.callback(self._timer_ISR)
        self.acquiring = True

    def record(self):
        """Start streaming data to computer."""
        self.data_chx.record()
        self.data_chy.record()
        if not self.acquiring:
            self._start_acquisition()
