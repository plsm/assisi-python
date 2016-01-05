#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A simple simulation environment with one fish.
"""

from assisipy import sim

import math

WALL_HEIGHT = 5
wall_id = 1

def create_small_wall (x, y, yaw, color):
    global wall_id
    simctrl.spawn (
        'Physical', 'Wall-{0}'.format (wall_id),
        (x, y, yaw),
        polygon = ((0.5, -0.5), (0.5, 0.5), (-.5, 0.5), (-.5, -.5)),
        color = color,
        height = WALL_HEIGHT)
    wall_id += 1

def create_long_wall (x, y, yaw, color):
    global wall_id
    simctrl.spawn (
        'Physical', 'Wall-{0}'.format (wall_id),
        (x, y, yaw),
        polygon = ((1.5, -0.5), (1.5, 0.5), (-1.5, 0.5), (-1.5, -.5)),
        color = color,
        height = WALL_HEIGHT)
    wall_id += 1

simctrl = sim.Control()
    
# Spawn the Fish
simctrl.spawn ('Fish', 'Fish-001', (3, 0, 0))
simctrl.spawn ('Fish', 'Fish-002', (0, -10, 0))
simctrl.spawn ('Fish', 'Fish-003', (0, 3, 0))
simctrl.spawn ('Fish', 'Fish-004', (0, -5, 1))

# create corridor
for x in range (-5, 5):
    create_small_wall (x,  2, 0, color = (1, 0, 0))
    create_small_wall (x, -2, 0, color = (1, 0, 1))

numberWalls = 36
openingSize = 6
for t in range (0, numberWalls):
    angle = 2 * math.pi * (t + numberWalls / 2 + openingSize) / (numberWalls + openingSize)
    create_long_wall (
        30 + 20 * math.cos (angle),
         20 * math.sin (angle), yaw = angle + math.pi / 2,
         color = (1, 0, 0))
    angle = 2 * math.pi * (t + openingSize / 2) / (numberWalls + openingSize)
    create_long_wall (
        -30 + 20 * math.cos (angle),
         20 * math.sin (angle), yaw = angle + math.pi / 2,
         color = (1, 0, 0))

#for y in range (-5, 5):
#    create_wall (6, y, color = (0, 0, 1))
