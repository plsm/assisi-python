#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A simple demo of a fish wandering around.  The fish moves in a sinusoidal path

from assisipy import fish
import util

import sys # For flushing the output buffer
import argparse
from time import sleep
from threading import Thread, Event
from math import pi

IDLE = 0
SWIMMING_RIGHT = 1
SWIMMING_LEFT = 2
TURNING_LEFT = 3
TURNING_RIGHT = 4

class WanderStraight (Thread):
    """
    A demo fish controller.

    Make the fish wander in straight sinusoidal path, outputing what it sees through its eyes.
    """

    def __init__ (self, fish_name, event):

        Thread.__init__(self)
        self.stopped = event

        self._fish = fish.Fish (name = fish_name)
        self._state = SWIMMING_LEFT
        self._turned = 0.0

        self.v_straight = 4.0
        self.v_turn = 0.2
        self.v_diff = 0.7

        self.Td = 0.1
        self.vision_update_rate = 10 # Output eyes readings 
                                   # every 10*Td
        self._update_count = 0

        (x, y, yaw) = self._fish.get_true_pose ()
        self._yaw = yaw
        self._turned = 0.0

        self.go_straight_left ()

    def go_straight_left (self):
        self._fish.set_vel (self.v_straight, self.v_straight * self.v_diff)

    def go_straight_right (self):
        self._fish.set_vel (self.v_straight * self.v_diff, self.v_straight)

    def turn_right (self):
        self._fish.set_vel (self.v_turn, -self.v_turn)

    def turn_left(self):
        self._fish.set_vel (-self.v_turn, self.v_turn)

    def update (self):
        """
        Update the fish state.

        Print debug information to standard output, compute the next state, and execute the state's action.
        
        """
        self._update_count += 1
        if self._update_count % self.vision_update_rate == 0:
#            print 'state %3d' % (self._state), self._fish.get_range (fish.ARRAY)
            print self._fish.get_eye (fish.LEFT_EYE)
        # compute next state
        if self._state == SWIMMING_RIGHT or self._state == SWIMMING_LEFT:
            if self._fish.get_range (fish.OBJECT_FRONT) < 5:
                #    \
                #or self._fish.get_range (fish.OBJECT_RIGHT_FRONT) < 2 \
                #or self._fish.get_range (fish.OBJECT_LEFT_FRONT) < 2:
                if self._fish.get_range (fish.OBJECT_RIGHT_FRONT) < 2:
                    self._state = TURNING_LEFT
                else:
                    self._state = TURNING_RIGHT
                self._turned = 0.0
            elif self._state == SWIMMING_RIGHT:
                self._state = SWIMMING_LEFT
            else:
                self._state = SWIMMING_RIGHT
        elif self._state == TURNING_LEFT or self._state == TURNING_RIGHT:
            (x, y, yaw) = self._fish.get_true_pose ()
            yaw_diff = util.wrap_to_pi (yaw - self._yaw)
            self._turned += yaw_diff
            self._yaw = yaw
            if abs (self._turned) > pi:
                self._state = SWIMMING_LEFT
        # act according to state
        if self._state == SWIMMING_RIGHT:
            self.go_straight_right ()
        elif self._state == SWIMMING_LEFT:
            self.go_straight_left ()
        elif self._state == TURNING_LEFT:
            self.turn_left ()
        elif self._state == TURNING_RIGHT:
            self.turn_right ()

    def run (self):
        # Run update every Td
        while not self.stopped.wait (self.Td):
            self.update()
        self._cleanup()

    def _cleanup (self):
        # Stop the fish
        self._fish.set_vel (0.0, 0.0)
        self.state = IDLE
        print ('Stopping...')



if __name__ == '__main__':

    # Parse command line arguments for fish name
    parser = argparse.ArgumentParser (
        description = 'A simple fish wander controller. Fish moves in straight sinusoidal lines until it encounters an obstacle ahead. It turns about 180 degrees to clear the obstacle, and then continues in a straight line.')
    parser.add_argument (
        '--fish_name',
        help = 'Fish name',
        default = 'Fish-001')
    args = parser.parse_args ()

    stop_flag = Event ()
    
    print("Press ENTER to stop the program at any time.")
    for i in range (2, 0, -1):
        print 'The fish controller will start in {0} seconds...\r'.format (i),
        sys.stdout.flush ()
        sleep (1)
    print ('\n')

    wanderer = WanderStraight (args.fish_name, stop_flag)
    wanderer.start ()

    # Python 2to3 workaround
    try:
        input = raw_input
    except NameError:
        pass
    input("\n")

    stop_flag.set()
