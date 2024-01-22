# 1-led-reward-association: lining speakers with the mid LED and release the reward.

from pyControl.utility import *
import hardware_definition as hw
from devices import *

# -------------------------------------------------------------------------
# States and events.
# -------------------------------------------------------------------------

states = ['trial',
          'led_on',
          'disengaged',
          'gap']

events = ['lick',
          'session_timer',
          'motion']

initial_state = 'trial'

# -------------------------------------------------------------------------
# Variables.
# -------------------------------------------------------------------------

# general parameters

# session params
v.session_duration = 45 * minute
v.reward_duration = 30 * ms
v.reward_number = 0
v.stim_dir = None
v.n_lick___ = 5
v.max_IT_duration = 10 * second
v.max_led_duration = 3 * second


# -------------------------------------------------------------------------
# Define behaviour.
# -------------------------------------------------------------------------


# Run start and stop behaviour.
def run_start():
    "Code here is executed when the framework starts running."
    set_timer('session_timer', v.session_duration, True)
    hw.audio.start()
    hw.cameraTrigger.start()
    hw.motionSensor.record()
    hw.visual.all_off()
    print('{}, CPI'.format(hw.motionSensor.sensor_x.CPI))
    hw.reward.reward_duration = v.reward_duration
    hw.motionSensor.threshold = 10

def run_end():
    """ 
    Code here is executed when the framework stops running.
    Turn off all hardware outputs.
    """
    hw.visual.all_off()
    hw.reward.stop()
    hw.motionSensor.off()
    hw.cameraTrigger.stop()
    hw.audio.all_off()
    hw.audio.stop()
    hw.off()

# State behaviour functions.

def trial(event):
    "beginning of the trial"
    if event == 'entry':
        v.stim_dir = None  # reset stim_dir, otherwise any lick will be rewarded, even before LED presentation
        hw.audio.cue(3)
        timed_goto_state('disengaged', v.max_IT_duration)
    elif event == 'motion' or event == 'lick':  # any action will start the trial
        goto_state('led_on')

def led_on(event):
    "turn on the led"
    if event == 'entry':
        hw.visual.cue(2)
        timed_goto_state('gap', v.max_led_duration)
        if v.n_lick___ >= 3:
            hw.reward.release()
            v.n_lick___ = 0
            v.reward_number += 1
            print('{}, reward_number'.format(v.reward_number))
    elif event == 'exit':
        hw.visual.all_off()

def disengaged(event):
    "disengaged state"
    if event == 'entry':
        hw.visual.all_off()
    elif event =='motion' or event == 'lick':
        goto_state('led_on')

def gap(event):
    "penalty state"
    if event == 'entry':
        hw.visual.all_off()
        timed_goto_state('trial', randint(v.max_led_duration, v.max_IT_duration))


# State independent behaviour.
def all_states(event):
    """
    Code here will be executed when any event occurs,
    irrespective of the state the machine is in.
    Executes before the state code.
    """
    if event == "lick":
        v.n_lick___ += 1
    elif event == 'session_timer':
        hw.motionSensor.stop()
        stop_framework()
