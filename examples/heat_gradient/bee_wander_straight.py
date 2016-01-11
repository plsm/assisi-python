#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A simple demo of bee-casu interaction.
# The bee is wandering around in straight lines. 
# If it sees an obstacle ahead, it turns approxmately 180 degrees,
# and continues moving in straight lines.
# It constantly outputs its heat sensor readings.

# Python 2 to 3 workarounds
from __future__ import print_function

from assisipy import bee

import sys # For flushing the output buffer
import argparse
from time import sleep
from threading import Thread, Event
from math import pi

IDLE = 0
WALKING = 1
TURNING = 2

def wrap_to_pi(angle):
    """
    Angle is in radians, in the interval [-2pi,2pi]
    """

    angle += 2*pi # We're in [0,4pi] now
    angle %= 2*pi # Now we're between [0,2*pi]
    
    if angle > pi:
        angle -= 2*pi

    return angle
    
class WanderStraight(Thread):
    """
    A demo bee controller.
    Makes the bee wander in straight lines, and outputs heat sensor readings.
    On encountering an obstacle, the bee turns approximately 180 degrees.
    Uses true pose information for turning!
    """

    def __init__(self, bee_name, event):
        
        Thread.__init__(self)
        self.stopped = event

        self._bee = bee.Bee(name = bee_name)
        self._state = WALKING
        self._turned = 0.0

        self.v_straight = 1.0
        self.v_turn = 0.2

        self.Td = 0.1
        self.heat_update_rate = 10 # Output heat sensor readings 
                                   # every 10*Td
        self._update_count = 0

        (x,y,yaw) = self._bee.get_true_pose()
        self._yaw = yaw
        self._turned = 0.0

        self.go_straight()

    def go_straight(self):
        self._bee.set_vel(self.v_straight,self.v_straight)

    def turn_right(self):
        self._bee.set_vel(self.v_turn,-self.v_turn)

    def turn_left(self):
        self._bee.set_vel(-self.v_turn,self.v_turn)

    def update(self):
        """
        The controller update function.
        """
        self._update_count += 1
        if self._state == WALKING:
            # Check sensors
            if self._bee.get_range(bee.OBJECT_FRONT) < 2:
                self.turn_left()
                self._turned = 0.0
                self._state = TURNING
        elif self._state == TURNING:
            (x,y,yaw) = self._bee.get_true_pose()
            yaw_diff = wrap_to_pi(yaw - self._yaw)
            self._turned += yaw_diff
            self._yaw = yaw
            if abs(self._turned) > pi:
                self._state = WALKING
                self.go_straight()
        if self._update_count % self.heat_update_rate == 0:
            print self._bee.get_temp(), self._bee.get_temp.gradient ()

    def run(self):
        # Run update every Td
        while not self.stopped.wait(self.Td):
            self.update()
        
        self._cleanup()

    def _cleanup(self):
        # Stop the bee
        
        self._bee.set_vel(0.0,0.0)
        self.state = IDLE
        
        print('Stopping...')

if __name__ == '__main__':

    # Parse command line arguments for bee name
    parser = argparse.ArgumentParser(description='A simple bee wander controller. Bee moves in straight lines until it encounters an obstacle ahead. It turns about 180 degrees to clear the obstacle, and then continues in a straight line.')
    parser.add_argument('--bee_name',help='Bee name',
                        default='Bee-001')
    args = parser.parse_args()

    stop_flag = Event()
    
    
    print("Press ENTER to stop the program at any time.")
    for i in reversed(range(1,4)):
        print("The bee controller will start in {0} seconds...\r".format(i), end="")
        sys.stdout.flush()
        sleep(1)
    print('\n')

    wanderer = WanderStraight(args.bee_name, stop_flag)
    wanderer.start()

    # Python 2to3 workaround
    try:
        input = raw_input
    except NameError:
        pass
    input("\n")

    stop_flag.set()


            

    
