# PyTreadmillTask

from pyControl.utility import *
import hardware_definition as hw
from devices import *
import math

# -------------------------------------------------------------------------
# States and events.
# -------------------------------------------------------------------------

states = ['trial_start',
          'reward']

events = ['lick',
          'session_timer',
          'IT_timer']

initial_state = 'trial_start'

# -------------------------------------------------------------------------
# Variables.
# -------------------------------------------------------------------------

# general parameters

# session params
v.session_duration = 45 * minute
v.reward_duration = 50 * ms


# intertrial params
v.gap_duration = 1 * second
v.max_IT_duration = 10 * second

# -------------------------------------------------------------------------
# State-independent Code
# -------------------------------------------------------------------------


def cue_random_led(LedDevice: LEDStim):
    """
    Cues 1 LED at a random direction
    """
    stim_dir = randint(0, LedDevice.n_directions - 1)
    LedDevice.all_off()
    LedDevice.cue_led(stim_dir)
    print('{}, LED_direction'.format(stim_dir))

    return stim_dir


# -------------------------------------------------------------------------
# Define behaviour.
# -------------------------------------------------------------------------


# Run start and stop behaviour.
def run_start():
    "Code here is executed when the framework starts running."
    set_timer('session_timer', v.session_duration, True)
    hw.motionSensor.record()
    hw.LED_Delivery.all_off()
    print('CPI={}'.format(hw.motionSensor.sensor_x.CPI))
    hw.reward.reward_duration = v.reward_duration



def run_end():
    """ 
    Code here is executed when the framework stops running.
    Turn off all hardware outputs.
    """
    hw.LED_Delivery.all_off()
    hw.reward.stop()
    hw.motionSensor.off()
    hw.off()

# State behaviour functions.

def trial_start(event):
    "beginning of the trial"
    if event == 'entry':
        cue_random_led(hw.LED_Delivery)
        set_timer('IT_timer', v.max_IT_duration, False)
    elif event =='exit':
        disarm_timer('IT_timer')
    elif event == 'IT_timer':  # if the animal didn't lick, a new LED is cued
        cue_random_led(hw.LED_Delivery)
    elif event == 'lick':
        goto_state('reward')

def reward(event):
    "reward state"
    if event == 'entry':
        hw.LED_Delivery.all_off()
        hw.reward.release()
        timed_goto_state('trial_start', v.gap_duration)

# State independent behaviour.
def all_states(event):
    """
    Code here will be executed when any event occurs,
    irrespective of the state the machine is in.
    """
    if event == 'session_timer':
        hw.motionSensor.stop()
        stop_framework()