from pyControl.hardware import Digital_input, Digital_output

class Lickometer():
    """
    Optical lickometer to detect lick events
    Device documentation on: https://sanworks.io/shop/viewproduct?productID=1020
    
    Configuration:
    Red wire: positive; Purple wire: negative
    Wires closer to the 4mm nut: emitter; wires further from: transistor
    
    # All purple wires --> GND
    # Transistor positive end --> Digital input port
    # Emitter positive end --> 500 ohm resistor --> Power source
    # Add a 40k pull-up resistor between power source and digital input
    """
    
    def __init__(self,  lick_port, sol_port, rising_event_A='lick_1', debounce=5, **kwargs):
        # Event triggered when pin is pulled down
        self.lick_1 = Digital_input(lick_port.DIO_A, rising_event_A, falling_event=None, debounce=debounce, pull=up)
        self.SOL_1  = Digital_output(sol_port.POW_A)
        self.SOL_1.off()