import utime
import pyControl.hardware as _h
from devices._audio_player import Audio_player

class AudioStim(Audio_player):
    "sound stimuli from 7 speakers using PyControl's `Audio_player`"
    def __init__(self, port: _h.Port):
        "initialise the audio player"
        super().__init__(port)
        self.set_volume(25)  # Between 1 - 30
        utime.sleep_ms(20)  # wait for the audio player to be ready

        pins = {0:'W59',    # Dir0
                1:'W55',    # Dir1
                2:'W7',    # Dir2
                3:'W58',    # Dir3
                4:'W56',    # Dir4
                5:'W64',    # Dir5
                6:'W62'}    # Dir6
        #the POW pins used so that their logic level is inverted automatically.
        powerlines = ('W18', 'W46', 'W62', 'W64','W30','W32')
        self.speakers = {}
        self.active = []
        for direction, pin in pins.items():
            self.speakers[direction] = _h.Digital_output(pin=pin, inverted=pin in powerlines)
            self.speakers[direction].off()

        # Start playing the audio file
        self.play(folder_num = 1, file_num = 1)  # Play file 1 from folder 3.
        utime.sleep_ms(20)  # wait for the audio player to be ready

    def start(self):
        "start playing"
        self.all_off()
        self.command(0x0D)  # start the playback

    def stop(self):
        "stop the playback"
        self.all_off()
        self.command(0x0C)  # reset the module

    def all_off(self):
        "turn off all Speakers"
        for spk in self.speakers.values():
            spk.off()
        self.active = []

    def all_on(self):
        "turn on all the Speakers"
        for spk in self.speakers.values():
            spk.on()
        self.active = list(self.speakers.keys())

    def cue(self, direction:int):
        "turn on the Speaker corresponding to the given direction"
        self.all_off()
        self.speakers[direction].on()
        self.active = [direction]

    def cue_array(self, arr:list):
        "turn on the all the speakers corresponding to the given directions in `arr`"
        self.all_off()
        self.active = []
        for d in arr:
            self.speakers[d].on()
            self.active.append(d)
