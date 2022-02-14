# PyTreadmillTask

from pyControl.utility import *
import hardware_definition as hw
from devices import *
import math
import uarray

# -------------------------------------------------------------------------
# States and events.
# -------------------------------------------------------------------------

states = ['intertrial']

events = ['motion',
          'session_timer']

initial_state = 'intertrial'

# -------------------------------------------------------------------------
# Variables.
# -------------------------------------------------------------------------

# session params
v.session_duration = 10 * second
v.motion_timer___ = 10 * ms  # polls motion every 1ms


# Run start and stop behaviour.
def run_start():
    # Code here is executed when the framework starts running.
    set_timer('session_timer', v.session_duration, True)
    hw.motionSensor.record()
    # set_timer('motion', v.motion_timer___)


def run_end():
    # Code here is executed when the framework stops running.
    # Turn off all hardware outputs.
    hw.motionSensor.off()
    hw.off()


# State behaviour functions.
def intertrial(event):
    if event == 'motion':
        # print('mo')
        pass


# State independent behaviour.
def all_states(event):
    # Code here will be executed when any event occurs,
    # irrespective of the state the machine is in.
    if event == 'motion':
        # read the motion registers and and append the variables
        print('dX={}; dY={}'.format(hw.motionSensor.x / hw.motionSensor.sensor.CPI * 2.54, hw.motionSensor.y / hw.motionSensor.sensor.CPI * 2.54))
        # set_timer('motion', v.motion_timer___)

    elif event == 'session_timer':
        stop_framework()