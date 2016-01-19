#!/usr/bin/env python
# -*- coding: utf-8 -*-

from assisipy import fish

import util
import common

import sys
import argparse
import scipy.special
import math
import random
import time
import signal

DW = 50
"""Threshold distance determining the interaction with the walls."""

KAPPA_0 = 6.3
"""Dispertion parameter associated with the basic-swimming behaviour."""

KAPPA_W = 20
"""Dispertion parameter associated with the wall-following behaviour."""

KAPPA_F = 2
"""Measure of concentration of perceived fish."""

KAPPA_S = 20
"""Dispertion parameter associated with perceived spots."""

I0K0 = scipy.special.i0 (KAPPA_0)
"""Modified Bessel function of first kind of order zero used with basic-swimming behaviour."""

I0KW = scipy.special.i0 (KAPPA_W)
"""Modified Bessel function of first kind of order zero used with wall-swimming behaviour."""

I0KF = scipy.special.i0 (KAPPA_F)
"""Modified Bessel function of first kind of order zero used with perceived fish."""

I0KS = scipy.special.i0 (KAPPA_S)
"""Modified Bessel function of first kind of order zero used with spots of interest."""

ALPHA_0 = 55
"""Weight of other fish on a focal fish distant from any wall."""

ALPHA_W = 20
"""Weight of other fish on a focal fish near a wall."""

BETA_0 = 0.15
"""Weight of a spot of interest on a focal fish distant from any wall."""

BETA_W = 0.01
"""Weight of a spot of interest on a focal fish near a wall."""

CAMERA_FIELD_OF_VIEW = 3 * math.pi / 4
"""Field of view of each fish eye."""

CAMERA_PIXEL_COUNT = 10
"""
Number of pixels of circular camera used by fish.

This should be equal to the value used by the playground.
"""

PDF_VECTOR_SIZE = 36
"""Size of the vector that contains the discretization of probability density function."""

PDF_VECTOR_SLOT_ANGLE = 2 * math.pi / PDF_VECTOR_SIZE
"""Angle covered by a slot of the discretization of probability density function."""

SPOT_DISTANCE_THRESHOLD = 50
"""."""

FISH_DISTANCE_THRESHOLD = 50

MAXIMUM_TURNING_ANGLE = math.pi / 2

## python 2.x quircks ...
perceivedObjects = []
currentObjectRun_StartAngle = None
currentObjectRun_OnFlag = False
sumSolidAngles = 0


class SchoolingVisual:
    """
    Fish controller based on Bertrand's model.

    The model is described in the paper
    
    Bertrand Collignon, Axel S\'eguret, and Jos\'e Halloy, Zebrafish
    collective behaviour in heterogeneous environment modeled by a
    stochastic model based on visual perception

    available at
    http://arxiv.org/abs/1509.01448

    The eyes are modeled by circular cameras that provide colour and
    distance information of perceived objects.  The two circular cameras
    cover a field of view of 270º.  The image provided by the cameras is
    stored in attributes eye_distance and eye_pixel.  These atributes are
    lists of lenght 2*CAMERA_PIXEL_COUNT.  The data contained in these
    lists is used to compute probability density functions (PD) for basic
    swiming behaviour, wall following behaviour, following other fish, and
    going to spots of interest.  The final discretised PDF is stored in
    attribute pdf_vector, a list of size PDF_VECTOR_SIZE.  A sample angle
    (constrained to the maximum turning angle of fish) is taken which is
    then converted to left and right motor velocities.
    """

    def __init__ (self, fish_name):
        """Construct a fish object that is going to control the given fish."""

        self._fish = fish.Fish (name = fish_name)

        self.v_straight = 4.0
        self.turn = 0

        self.Td = 0.3

        (x, y, yaw) = self._fish.get_true_pose ()
        
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

        Print debug information to standard output, compute the next state,
        and execute the state's action.
        """
        self.compute_eye_data ()
        self.compute_pdf ()
        self.sample_pdf ()
        self.swim ()

    def compute_eye_data (self):
        """
        Calculate lists eye_distance and eye_pixel from the data collected
        by the two eyes.

        The eyes are modeled by circular cameras that provide colour and
        distance information of perceived objects.
        """
        self.eye_pixel, self.eye_distance = self._fish.get_pixels ()


    def compute_pdf (self):
        """
        Compute the probability density function that is used to calculate
        the angle the fish turns to.

        The probability density function is stored has a list of integers.
        
        Divide the probability density function after its components have been computed.
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
        Sample an angle from the probability density function and return a
        number between zero and PDF_VECTOR_SIZE.

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
        """Print fish state."""
        for p in self.pdf_vector:
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
        
    def is_wall (self, index):
        """
        Returns True if the fish perceives a wall at the following angle
        """
        return util.similar_colour (self.eye_pixel [index], common.WALL_COLOUR)
    
    def is_fish (self, index):
        """
        Returns True if the fish perceives a fish at the given index.

        Parameters
           index -- index to list self.eye_pixel that contains colour
           information.
        """
        return util.similar_colour (self.eye_pixel [index], common.FISH_COLOUR)

    def is_spot (self, index):
        """
        Returns True if the fish perceis a spot at the pixel at the given index.

        Parameters
           index -- index to list self.eye_pixel that contains colour
           information.
        """
        return util.similar_colour (self.eye_pixel [index], common.SPOT_COLOUR)


    def pdf_f0 (self):
        """
        Compute the probability density Function f0(theta) for a fish
        to move in each potential direction in a bounded tank without
        perceptible stimuli.
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
        Compute the probability density function fF(theta) for perceived fish.
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
        Compute the probability density Function for spots of interest.
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
        General method to process camera data and return a list with
        perceived objects.

        For each perceived object we return the angle where it was
        perceived and the opening angle of the perceived object.

        Parameters
           isObjectFunction -- function that classifies pixel colours.

           objectThreshold -- if two adjacent pixels are classified as
           objects they belong to different objects if the corresponding
           distance is higher than this threshold.
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
        """Main function that runs the fish behaviour."""
        while True:
            # Run update every Td
            time.sleep (self.Td)
            self.update ()

    def _cleanup (self):
        self._fish.set_vel (0.0, 0.0)

def cleanup (signal, frame):
    """Signal handler to finish the program cleanly."""
    schooling._cleanup ()
    print ('Stopping...')
    sys.exit (0)
    

if __name__ == '__main__':

    # Parse command line arguments for fish name
    parser = argparse.ArgumentParser (
        description = 'A simple fish wander controller. Fish moves in straight sinusoidal lines until it encounters an obstacle ahead. It turns about 180 degrees to clear the obstacle, and then continues in a straight line.')
    parser.add_argument (
        '--fish_name',
        help = 'Fish name',
        default = 'Fish-001')
    args = parser.parse_args ()

    for i in range (2, 0, -1):
        print 'The fish controller will start in {0} seconds...\r'.format (i),
        sys.stdout.flush ()
        time.sleep (1)
    print ('\n')

    signal.signal (signal.SIGINT, cleanup)
    signal.signal (signal.SIGTERM, cleanup)
    schooling = SchoolingVisual (args.fish_name)
    schooling.run ()
