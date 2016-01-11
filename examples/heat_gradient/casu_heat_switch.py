#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A simple demo of Casu for using the Casu peltier actuator.
Every 2 minutes, the Casu switches its peltier actuator between heating (38C) and cooling (28C).

While heating, the status LED is lit red, while cooling, it's lit blue.
"""

from __future__ import print_function

from assisipy import casu

from time import sleep
from threading import Thread, Event

COOLING = 0
HEATING = 1

class CasuController(Thread):
    """ 
    A demo Casu controller.
    Implements simple peltier on/off toggling.
    """

    def __init__(self, rtc_file, event):

        Thread.__init__(self)
        self.stopped = event

        self._casu = casu.Casu(rtc_file)
        self.Td = 120 # Switch every two minutes
        self.hot = 38
        self.cold = 28
        self._state = COOLING
        self.toggle_heater()

    def toggle_heater(self):
        if self._state == COOLING:
            self._casu.set_temp(self.hot)
            self._casu.set_diagnostic_led_rgb(r = 1)
            self._state = HEATING
            print('Heating up to 38 degrees.')
        else:
            self._casu.set_temp(self.cold)
            self._casu.set_diagnostic_led_rgb(b = 1)
            self._state = COOLING
            print('Cooling down to 28 degrees.')

    def run(self):
        # Toggle the heater every Td
        while not self.stopped.wait(self.Td):
            self.toggle_heater()

        self._casu.temp_standby()
        print('Turned off heater, exiting...')

if __name__ == '__main__':

    stop_flag = Event()
    print("Press ENTER to stop the program at any time.")

    ctrl = CasuController('casu.rtc', stop_flag)
    ctrl.start()

    # Python 2to3 workaround
    try:
        input = raw_input
    except NameError:
        pass
    input("")

    stop_flag.set()



            

    
