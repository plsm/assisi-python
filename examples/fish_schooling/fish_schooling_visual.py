#!/usr/bin/env python
# -*- coding: utf-8 -*-

from assisipy import fish

import util
import common

import sys # For flushing the output buffer
import argparse
import scipy.special
import math
import random
import time
from threading import Thread, Event


DW = 50
"""
threshold distance determining the interaction with the walls
"""

KAPPA_0 = 6.3
"""
dispertion parameter associated with the basic-swimming behaviour
"""

KAPPA_W = 20
"""
dispertion parameter associated with the wall-following behaviour
"""

KAPPA_F = 2

KAPPA_S = 20

I0K0 = scipy.special.i0 (KAPPA_0)

I0KW = scipy.special.i0 (KAPPA_W)

I0KF = scipy.special.i0 (KAPPA_F)

I0KS = scipy.special.i0 (KAPPA_S)

ALPHA_0 = 55
"""
Weight of other fish on a focal fish distant from any wall.
"""

ALPHA_W = 20
"""
Weight of other fish on a focal fish near a wall
"""

BETA_0 = 0.15
"""
Weight of a spot of interest on a focal fish distant from any wall.
"""

BETA_W = 0.01
"""
Weight of a spot of interest on a focal fish near a wall.
"""

CAMERA_FIELD_OF_VIEW = 3 * math.pi / 4

CAMERA_PIXEL_COUNT = 10

PDF_VECTOR_SIZE = 36
"""
Vector size that contains the discretization of Probability Distribution Function.
"""

PDF_VECTOR_SLOT_ANGLE = 2 * math.pi / PDF_VECTOR_SIZE
"""
Angle covered by a slot of the discretization of Probability Distribution Function.
"""

SPOT_DISTANCE_THRESHOLD = 50

FISH_DISTANCE_THRESHOLD = 50


## python 2.x quircks ...
perceivedObjects = []
currentObjectRun_StartAngle = None
currentObjectRun_OnFlag = False
sumSolidAngles = 0


KILL = False

class SchoolingVisual (Thread):
    """
    A demo fish schooling controller
    """

    def __init__ (self, fish_name, event):

        Thread.__init__(self)
        self.stopped = event

        self._fish = fish.Fish (name = fish_name)
        self._turned = 0.0

        self.v_straight = 4.0
        self.turn = 0
        self.v_turn = 0.2
        self.v_diff = 0.7

        self.Td = 0.3
        self.vision_update_rate = 10 # Output eyes readings every 10*Td
        self._update_count = 0

        (x, y, yaw) = self._fish.get_true_pose ()
        self._yaw = yaw
        self._turned = 0.0
        
        self.eye_distance = []
        self.eye_pixel = []

        self.pdf_vector = [0 for x in range (PDF_VECTOR_SIZE)]
        self.sumSolidAngles_Spots = 0
        self.sumSolidAngles_Fish = 0
        self.nearWall = False
        self.alpha = -1
        self.beta = -1

    def update (self):
        """
        Update the fish state.

        Print debug information to standard output, compute the next state, and execute the state's action.
        
        """
        self.compute_eye_data ()
        self.compute_pdf ()
        self.sample_pdf ()
        self.swim ()
        global KILL
        if KILL:
            sys.exit ()



    def compute_eye_data (self):
        """
        Calculate lists eye_distance and eye_pixel from the data collected by the two eyes.

        The eyes are modeled by circular cameras that provide colour and distance information of perceived objects.
        """
        self.eye_pixel, self.eye_distance = self._fish.get_pixels ()
#        self.eye_distance = []
#        self.eye_pixel = []
#        for eye in [fish.LEFT_EYE, fish.RIGHT_EYE]:
#            for d in self._fish.get_eye (eye).distance:
#                self.eye_distance.append (d)
#            for p in self._fish.get_eye (eye).pixel:
#                self.eye_pixel.append (p)
        if len (self.eye_pixel) != 2 * CAMERA_PIXEL_COUNT:
            print "??!!!#@*!", len (self.eye_pixel), " = ", len (self._fish.get_eye (fish.LEFT_EYE).pixel), " + ", len (self._fish.get_eye (fish.RIGHT_EYE).pixel), \
              ' distance ', len (self.eye_distance), " = ", len (self._fish.get_eye (fish.LEFT_EYE).distance), " + ", len (self._fish.get_eye (fish.RIGHT_EYE).distance)
#        print self.eye_pixel [0].red, self.eye_pixel [0].green, self.eye_pixel [0].blue
#        print self.eye_distance
#        print self._fish.get_eye (fish.LEFT_EYE)


    def compute_pdf (self):
        """
        Compute the probability distribution function that is used to calculate the angle the fish turns to.

        The probability distribution function is stored has a list of integers.
        
        Divide the Probability Distribution Function after its components have been computed.
        """
        self.pdf_vector = [0 for x in range (PDF_VECTOR_SIZE)]
        self.pdf_f0 ()
        if self.nearWall:
            self.alpha = ALPHA_W
            self.beta = BETA_W
        else:
            self.alpha = ALPHA_0
            self.beta = BETA_0
        self.pdf_fF ()
        self.pdf_fS ()
        for index in range (PDF_VECTOR_SIZE):
            self.pdf_vector [index] /= 1 + self.alpha * self.sumSolidAngles_Fish + self.beta * self.sumSolidAngles_Spots

    def sample_pdf (self):
        """
        Sample an angle from the Probability Distribution Function and return a number between zero and PDF_VECTOR_SIZE.

        The corresponding angle is given by
        
        -math.pi + index * PDF_VECTOR_SLOT_ANGLE
        
        where index is the returned number.
        """
        sumSlots = 0
        for s in self.pdf_vector:
            sumSlots += s
        rnd = sumSlots * random.random ()
        index = 0
        go = True
        sumSlots = 0
        while go:
            sumSlots += self.pdf_vector [index]
            if sumSlots < rnd:
                index += 1
            else:
                go = False
        self.turn = index
    
    def swim (self):
        """
        Turn the robot in the direction that was sampled using the PDF.
        """
        cf = math.sin (math.pi * time.clock () / 4) + self.turn
        if self.turn < PDF_VECTOR_SIZE / 2:
            lf = 1.0
            rf = 4.0 * (self.turn - PDF_VECTOR_SIZE / 4.0) / PDF_VECTOR_SIZE
        else:
            lf = 4.0 * (3 * PDF_VECTOR_SIZE / 4.0 - self.turn) / PDF_VECTOR_SIZE
            rf = 1.0
        self._fish.set_vel (lf * self.v_straight, rf * self.v_straight)
#        print 'index = %2d,  angle is %4dº,  motors %5.2f %5.2f' % (self.turn, math.degrees (-math.pi + self.turn * PDF_VECTOR_SLOT_ANGLE), lf, rf)

    def print_data (self):
        stop = False
        for p in self.pdf_vector:
            if math.isnan (p):
                print ' NaN'
                stop = True
            else:
                print '%4d' % (int (100 * p)),
        print
        print 'nearWall = ', self.nearWall, '  sumSolidAngles_Spots =', self.sumSolidAngles_Spots, ' sumSolidAngles_Fish =', self.sumSolidAngles_Fish
        if self.nearWall or True:
            print 'dista',
            for d in self.eye_distance:
                print '%6d' % (int (d)),
            print
            print 'pixel',
            for c in self.eye_pixel:
                print '%2d%2d%2d' % (int (10 * c.red), int (10 * c.green), int (10 * c.blue)),
            print
        if stop:
            str2 = raw_input ("escreve")
            print str2
        
    def is_wall (self, angle):
        """
        Returns True if the fish perceives a wall at the following angle
        """
        return util.similar_colour (self.eye_pixel [angle], common.WALL_COLOUR)
    
    def is_fish (self, angle):
        """
        Returns True if the fish perceives a fish at the following angle
        """
        return util.similar_colour (self.eye_pixel [angle], common.FISH_COLOUR)

    def is_spot (self, index):
        return util.similar_colour (self.eye_pixel [index], common.SPOT_COLOUR)


    def pdf_f0 (self):
        """
        Compute the PDF f0(theta) for a fish to move in each potential direction in a bounded tank without perceptible stimuli
        """
        # see if the fish perceives a wall
        angle = CAMERA_FIELD_OF_VIEW
        step = -CAMERA_FIELD_OF_VIEW / CAMERA_PIXEL_COUNT
        distanceClosestWall = None
        angleClosestWall = None
        for index in range (2 * CAMERA_PIXEL_COUNT):
            value = 0
            if self.is_wall (index) \
              and (distanceClosestWall == None \
                   or (distanceClosestWall != None \
                       and distanceClosestWall > self.eye_distance [index])):
                distanceClosestWall = self.eye_distance [index]
                angleClosestWall = angle
            angle += step
        self.nearWall = distanceClosestWall != None and distanceClosestWall <= DW
        # compute PDF f0(theta)
        angle = -math.pi
        if not self.nearWall:
            for index in range (PDF_VECTOR_SIZE):
                self.pdf_vector [index] += \
                  math.exp (KAPPA_0 * math.cos (angle)) \
                  / (2 * math.pi * I0K0)
                angle += PDF_VECTOR_SLOT_ANGLE
        else:
            wallAngle1 = angleClosestWall + math.pi / 2
            wallAngle2 = angleClosestWall - math.pi / 2
            for index in range (PDF_VECTOR_SIZE):
                self.pdf_vector [index] += \
                    (math.exp (KAPPA_W * math.cos (angle - wallAngle1)) \
                    + math.exp (KAPPA_W * math.cos (angle - wallAngle2))) \
                    / (2 * 2 * math.pi * I0K0)
                angle += PDF_VECTOR_SLOT_ANGLE

    def pdf_fF (self):
        """
        Compute the Probability Distribution Function fF(theta) for perceived fish.
        """
        perceivedFish, self.sumSolidAngles_Fish = self.computeObjects (self.is_fish, FISH_DISTANCE_THRESHOLD)
        if perceivedFish != []:
            angle = -math.pi
            for index in range (PDF_VECTOR_SIZE):
                for (mu, solidAngle) in perceivedFish:
                    self.pdf_vector [index] += \
                        self.alpha \
                        * solidAngle \
                        * math.exp (KAPPA_F * math.cos (angle - mu)) \
                        / (2 * math.pi * I0KF)
                angle += PDF_VECTOR_SLOT_ANGLE

    def pdf_fS (self):
        """
        Compute the Probability Distribution Function for spots of interest.
        """
        perceivedSpots, self.sumSolidAngles_Spots = self.computeObjects (self.is_spot, SPOT_DISTANCE_THRESHOLD)
        if perceivedSpots != []:
            angle = -math.pi
            for index in range (PDF_VECTOR_SIZE):
                for (mu, solidAngle) in perceivedSpots:
                    self.pdf_vector [index] += \
                        self.beta \
                        * solidAngle \
                        * math.exp (KAPPA_S * math.cos (angle - mu)) \
                        / (2 * math.pi * I0KS)
                angle += PDF_VECTOR_SLOT_ANGLE

            
    def computeObjects (self, isObjectFunction, objectThreshold):
        """
        Process camera data and return a list with perceived objects.

        For each perceived object we return the angle where it was perceived and the opening angle of the perceived object.
        """
        # python 2.x hack
        global currentObjectRun_StartAngle
        global perceivedObjects
        global currentObjectRun_OnFlag
        global sumSolidAngles
        sumSolidAngles = 0
        perceivedObjects = []
        currentObjectRun_MaxDistance = None
        currentObjectRun_MinDistance = None
        currentObjectRun_StartAngle = None
        currentObjectRun_OnFlag = False
        def addCurrentObjectRun (endAngle):
            # in python 3.x this is nonlocal
            global currentObjectRun_StartAngle
            global perceivedObjects
            global currentObjectRun_OnFlag
            global sumSolidAngles
            mu = (currentObjectRun_StartAngle + endAngle) / 2
            solidAngle = currentObjectRun_StartAngle - endAngle + PDF_VECTOR_SLOT_ANGLE
            t = (mu, solidAngle)
            perceivedObjects.append (t)
            currentObjectRun_OnFlag = False
            sumSolidAngles += solidAngle
        
        angle = CAMERA_FIELD_OF_VIEW
        step = -CAMERA_FIELD_OF_VIEW / CAMERA_PIXEL_COUNT
        for index in range (2 * CAMERA_PIXEL_COUNT):
            if isObjectFunction (index):
                if currentObjectRun_OnFlag \
                   and max (currentObjectRun_MaxDistance, self.eye_distance [index]) - min (currentObjectRun_MinDistance, self.eye_distance [index]) > objectThreshold:
                    addCurrentObjectRun (angle - step)
                if not currentObjectRun_OnFlag:
                    currentObjectRun_OnFlag = True
                    currentObjectRun_StartAngle = angle
                    currentObjectRun_MaxDistance = self.eye_distance [index]
                    currentObjectRun_MinDistance = self.eye_distance [index]
                else:
                    currentObjectRun_MaxDistance = max (currentObjectRun_MaxDistance, self.eye_distance [index])
                    currentObjectRun_MinDistance = min (currentObjectRun_MinDistance, self.eye_distance [index])
            elif currentObjectRun_OnFlag:
                addCurrentObjectRun (angle - step)
            angle += step
        if currentObjectRun_OnFlag:
            addCurrentObjectRun (angle - step)
        return (perceivedObjects, sumSolidAngles)
    
    def run (self):
        # Run update every Td
        while not self.stopped.wait (self.Td):
            self.update ()
        self._cleanup ()

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
        time.sleep (1)
    print ('\n')

    schooling = SchoolingVisual (args.fish_name, stop_flag)
    schooling.start ()

    # Python 2to3 workaround
    try:
        input = raw_input
    except NameError:
        pass
    input("\n")

    stop_flag.set()


    
