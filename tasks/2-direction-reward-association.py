# PyTreadmillTask

from pyControl.utility import *
import hardware_definition as hw
from devices import *
import math

# -------------------------------------------------------------------------
# States and events.
# -------------------------------------------------------------------------

states = ['disengaged',
          'penalty',
          'led_on',
          'reward']

events = ['motion',
          'lick',
          'session_timer']

initial_state = 'disengaged'

# -------------------------------------------------------------------------
# Variables.
# -------------------------------------------------------------------------

# general parameters
v.target_angle___ = {0: math.pi / 4,
                     1: math.pi / 4,
                     2: math.pi / 4,
                     3: 3 * math.pi / 4,
                     4: 3 * math.pi / 4}
v.led_cues___ = list(v.target_angle___.keys())

v.audio_f_range___ = (10000, 20000)  # between 10kHz and 20kHz, loosely based on Heffner & Heffner 2007

# session params
v.session_duration = 1 * hour
v.reward_duration = 30 * ms
v.trial_number = 0
v.reward_number = 0
v.led_direction = -1


# intertrial params
v.min_IT_movement = 10  # cm - must be a multiple of 5
v.min_IT_duration = 3 * second
v.max_IT_duration = 25 * second
v.n_lick___ = 5
v.n_motion___ = 0

# trial params
v.max_led_duration = 10 * second
v.min_motion = 5  # cm - minimum distance to trigger an event
v.distance_to_target = 40  # cm - must be a multiple of 5
v.max_motion___ = int(v.distance_to_target / v.min_motion)
v.target_angle_tolerance = math.pi / 4  # rad
v.run_angle = 0

# -------------------------------------------------------------------------
# State-independent Code
# -------------------------------------------------------------------------


def cue_left_right(LedDevice: LEDStim):
    """
    Cues the right leds or the left leds, randomly.
    centre led always cued
    """
    LedDevice.all_off()
    if random() >= 0.5:
        cues = v.led_cues___[:3]
        out = 1
    else:
        cues = v.led_cues___[-3:]
        out = 3

    print('{}, LED_direction'.format(cues))
    LedDevice.cue_array(cues)

    return out

def arrived_to_target():
    """
    checks the motion direction against the target direction
    MUST have 5 stim directions
    """
    if abs(v.run_angle - v.target_angle___[v.led_direction]) < v.target_angle_tolerance:
        return True
    else:
        return False


def audio_feedback():
    """ Set the audio frequency based on the direction of the movement. """
    audio_freq = v.audio_f_range___[0] + (v.audio_f_range___[0] * v.run_angle / math.pi)
    hw.speaker.sine(audio_freq)


# -------------------------------------------------------------------------
# Define behaviour.
# -------------------------------------------------------------------------


# Run start and stop behaviour.
def run_start():
    "Code here is executed when the framework starts running."
    set_timer('session_timer', v.session_duration, True)
    hw.motionSensor.record()
    hw.speaker.set_volume(60)
    hw.speaker.off()
    hw.LED_Delivery.all_off()
    print('{}, CPI'.format(hw.motionSensor.sensor_x.CPI))
    hw.reward.reward_duration = v.reward_duration

def run_end():
    """ 
    Code here is executed when the framework stops running.
    Turn off all hardware outputs.
    """
    hw.LED_Delivery.all_off()
    hw.reward.stop()
    hw.speaker.off()
    hw.motionSensor.off()
    hw.off()

# State behaviour functions.

def led_on(event):
    "stimulation onset"
    if event == 'entry':
        timed_goto_state('disengaged', v.max_IT_duration)
        hw.speaker.set_volume(45)
        v.trial_number += 1
        print('{}, trial_number'.format(v.trial_number))
        timed_goto_state('disengaged', v.max_IT_duration)
        v.led_direction = cue_left_right(hw.LED_Delivery)
        v.n_motion___ = 0
        hw.motionSensor.delta_x = 0
        hw.motionSensor.delta_y = 0
        hw.motionSensor.threshold = v.min_motion

    elif event == 'motion':
        if v.n_motion___ <= v.max_motion___:
            arrived = arrived_to_target()
            audio_feedback()
            if arrived:
                goto_state('reward')
        else:
            goto_state('penalty')

def reward(event):
    "reward state"
    if event == 'entry':
        hw.LED_Delivery.all_off()
        hw.speaker.off()
        hw.motionSensor.threshold = v.distance_to_target
        if v.n_lick___ >= 3:
            hw.reward.release()
            v.n_lick___ = 0
            v.reward_number += 1
            print('{}, reward_number'.format(v.reward_number))
        timed_goto_state('led_on', randint(v.min_IT_duration, v.max_led_duration))


def penalty(event):
    "penalty state"
    if event == 'entry':
        hw.LED_Delivery.all_off()
        hw.speaker.off()
        hw.speaker.set_volume(55)
        hw.speaker.sine(5000)
        hw.motionSensor.threshold = v.distance_to_target
        timed_goto_state('led_on', v.max_led_duration)

def disengaged(event):
    "disengaged state"
    if event == 'entry':
        hw.LED_Delivery.all_off()
        hw.speaker.off()
    elif event =='motion' or event == 'lick':
        goto_state('led_on')


# State independent behaviour.
def all_states(event):
    """
    Code here will be executed when any event occurs,
    irrespective of the state the machine is in - before the state function is run.
    """
    if event == 'motion':
        # read the motion registers
        # to convert to cm, divide by CPI and multiply by 2.54
        # v.x___ = hw.motionSensor.x / hw.motionSensor.sensor_x.CPI * 2.54
        # v.y___ = hw.motionSensor.y / hw.motionSensor.sensor_x.CPI * 2.54
        v.n_motion___ += 1
        v.run_angle = math.atan2(hw.motionSensor.x, -hw.motionSensor.y)
        print('{}, run_angle_rad'.format(v.run_angle))

    elif event == 'lick':
        v.n_lick___ += 1
    elif event == 'session_timer':
        hw.motionSensor.stop()
        stop_framework()
