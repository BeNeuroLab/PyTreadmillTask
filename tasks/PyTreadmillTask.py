# PyTreadmillTask

from pyControl.utility import *
import hardware_definition as hw
from devices import *
import math
import uarray

# -------------------------------------------------------------------------
# States and events.
# -------------------------------------------------------------------------

states = ['intertrial',
          'trial_start',
          'odour_release',
          'reward',
          'penalty']

events = ['motion',
          'lick',
          'lick_off',
          'session_timer',
          'IT_timer',
          'odour_timer',
          'reward_timer'
          ]

initial_state = 'intertrial'

# -------------------------------------------------------------------------
# Variables.
# -------------------------------------------------------------------------

# general parameters
v.target_angle___ = {0: 5 * math.pi / 6,
                     1: 2 * math.pi / 3,
                     2: math.pi / 2,
                     3: math.pi / 3,
                     4: math.pi / 6}

v.audio_f_range___ = (10000, 20000)  # between 10kHz and 20kHz, loosely based on Heffner & Heffner 2007

# session params
v.session_duration = 1 * hour
v.reward_duration = 100 * ms
v.penalty_duration = 10 * second
v.trial_number = 0
v.motion_timer___ = 1 * ms  # polls motion every 1ms
v.new_motion___ = False  # flag to declare new motion
v.delta_x = uarray.array('i')  # signed int minimum 2 bytes
v.delta_y = uarray.array('i')

# intertrial params
v.min_IT_movement = 10  # cm
v.min_IT_duration = 1 * second
v.IT_duration_done___ = False

# trial params
v.max_odour_time = 10 * second
v.max_odour_movement = 50  # cm
v.distance_to_target = 20  # cm
v.target_angle_tolerance = math.pi / 18  # deg_rad
v.odourant_direction = -1
v.air_off_duration = 100 * ms

# -------------------------------------------------------------------------
# State-independent Code
# -------------------------------------------------------------------------


def release_single_odourant_random(odourDevice: ParallelOdourRelease):
    """
    Releases 1 odourant at a random direction
    """
    stimDir = randint(0, odourDevice.Ndirections - 1)
    odourDevice.all_off()
    odourDevice.odour_release(stimDir)

    print('{}, odourant_direction'.format(stimDir))

    return stimDir


def arrived_to_target(dX: float, dY: float,
                      odourant_direction: int,
                      distance_to_target: float,
                      target_angle_tolerance: float):
    """
    checks the motion critereon
    MUST have 5 odour directions
    """
    assert odourant_direction < 5, 'wrong direction value'

    movement = math.sqrt(dX**2 + dY**2)
    if movement < distance_to_target:
        return None

    else:
        move_angle = math.atan2(dY, dX)
        if abs(move_angle - v.target_angle___[odourant_direction]) < target_angle_tolerance:
            return True
        else:
            return False


def audio_mapping(d_a: float) -> float:
    """
    freq = (-10kHz/300)d_a + 15kHz
    """
    return mean(v.audio_f_range___) - (v.audio_f_range___[0] * d_a / v.target_angle___[0] * 2)


def audio_feedback(speaker,
                   dX: float, dY: float,
                   odourant_direction: int):
    angle = math.atan2(dY, dX)
    audio_freq = audio_mapping(angle - v.target_angle___[odourant_direction])
    speaker.sine(audio_freq)


# -------------------------------------------------------------------------
# Define behaviour.
# -------------------------------------------------------------------------


# Run start and stop behaviour.
def run_start():
    # Code here is executed when the framework starts running.
    set_timer('session_timer', v.session_duration, True)
    hw.motionSensor.power_up()
    hw.speaker.set_volume(90)
    hw.speaker.off()
    hw.odourDelivery.clean_air_on()
    set_timer('motion', v.motion_timer___)


def run_end():
    # Code here is executed when the framework stops running.
    # Turn off all hardware outputs.
    hw.odourDelivery.all_off()
    hw.rewardSol.off()
    hw.speaker.off()
    hw.motionSensor.shut_down()
    hw.off()


# State behaviour functions.
def intertrial(event):
    if event == 'entry':
        # coded so that at this point, there is clean air coming from every direction
        set_timer('IT_timer', v.min_IT_duration)
        v.IT_duration_done___ = False
    elif event == 'exit':
        disarm_timer('IT_timer')
    elif event == 'lick':
        # TODO: handle the lick data better
        pass
    elif event == 'IT_timer':
        v.IT_duration_done___ = True
        v.delta_x, v.delta_y = uarray.array('i'), uarray.array('i')
    elif event == 'motion':
        if v.IT_duration_done___ and v.new_motion___:
            if math.sqrt((sum(v.delta_x)**2) + (sum(v.delta_x)**2)) >= v.min_IT_movement:
                goto_state('trial_start')


def trial_start(event):
    if event == 'entry':
        v.delta_x, v.delta_y = uarray.array('i'), uarray.array('i')
        v.trial_number += 1
        print('{}, trial_number'.format(v.trial_number))
        hw.odourDelivery.all_off()
        timed_goto_state('odour_release', v.air_off_duration)


def odour_release(event):
    if event == 'entry':
        set_timer('odour_timer', v.max_odour_time)
        v.odourant_direction = release_single_odourant_random(hw.odourDelivery)
        v.delta_x, v.delta_y = uarray.array('i'), uarray.array('i')
    elif event == 'exit':
        disarm_timer('odour_timer')
        hw.speaker.off()
    elif event == 'motion':
        if v.new_motion___:
            D_x = sum(v.delta_x)
            D_y = sum(v.delta_y)
            arrived = arrived_to_target(D_x, D_y,
                                        v.odourant_direction,
                                        v.distance_to_target,
                                        v.target_angle_tolerance)

            audio_feedback(hw.speaker, D_x, D_y, v.odourant_direction)

            if arrived is None:
                pass
            elif arrived is True:
                goto_state('reward')
            elif arrived is False:
                goto_state('penalty')
    elif event == 'odour_timer':
        goto_state('penalty')


def reward(event):
    if event == 'entry':
        hw.odourDelivery.clean_air_on()
        set_timer('reward_timer', v.reward_duration, False)
        hw.rewardSol.on()
        print('{}, reward_on'.format(get_current_time()))
    elif event == 'exit':
        disarm_timer('reward_timer')
    elif event == 'reward_timer':
        hw.rewardSol.off()
        goto_state('intertrial')


def penalty(event):
    if event == 'entry':
        hw.odourDelivery.clean_air_on()
        print('{}, penalty_on'.format(get_current_time()))
        timed_goto_state('intertrial', v.penalty_duration)


# State independent behaviour.
def all_states(event):
    # Code here will be executed when any event occurs,
    # irrespective of the state the machine is in.
    if event == 'motion':
        # read the motion registers and and append the variables
        delta_x, delta_y = hw.motionSensor.read_pos()
        if delta_x == 0 and delta_y == 0:
            v.new_motion___ = False
        else:
            print('{},{}, dM'.format(delta_x, delta_y))
            v.delta_x.append(delta_x)
            v.delta_y.append(delta_y)
            v.new_motion___ = True
        set_timer('motion', v.motion_timer___)

    elif event == 'session_timer':
        stop_framework()
