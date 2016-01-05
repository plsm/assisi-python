#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A simulation environment with two rooms and several fish.
"""

import common

from assisipy import sim
import util

import argparse
import random
import math

COLLISION_THRESHOLD = 40

roomRadius = 20
roomCenterX = 30
ROOM_FRACTION = 4.0 / 5
    
def compute_room_specs (arenaRadius):
    global roomRadius
    global roomCenterX
    roomRadius = ROOM_FRACTION * arenaRadius / 2
    roomCenterX = arenaRadius - roomRadius


def spawn_fish (simctrl, numberFish):
    result = 0
    pickedCoordinates = []
    collisions = 0
    spawned = 0
    while spawned < numberFish and collisions < COLLISION_THRESHOLD:
        go = True
        collisions = 0
        while collisions < COLLISION_THRESHOLD and go:
            dist = roomRadius * random.random ()
            angle = 2 * math.pi * random.random ()
            side = random.choice ([roomCenterX, -roomCenterX])
            x = side + dist * math.cos (angle)
            y = dist * math.sin (angle)
            yaw = 2 * math.pi * random.random ()
            go = False
            for (xi, yi) in pickedCoordinates:
                if (x - xi) ** 2 + (y - yi) ** 2 < 10:
                    go = True
                    break
            if go:
                collisions += 1
        if collisions < COLLISION_THRESHOLD:
            pickedCoordinates.append ((x, y))
            spawned += 1
            fishName = 'Fish-%03d' % (spawned)
            simctrl.spawn ('Fish', fishName, (x, y, yaw))
    return spawned

def spawn_control_fish (simctrl):
    x = 0
    y = 4
    yaw = 0
    yaw = math.pi / 4
    fishName = 'Fish-001'
    simctrl.spawn ('Fish', fishName, (x, y, yaw))
    x = 10
    y = 6
    yaw = math.pi / 2
    fishName = 'Fish-002'
    simctrl.spawn ('Fish', fishName, (x, y, yaw))

def build_rooms (simctrl):
    """
    Create two rooms along the x axis joined by a small corridor.
    """
    numberWalls = 66
    openingSize = 6
    for t in range (0, numberWalls + 1):
        angle = 2 * math.pi * (t + numberWalls / 2 + openingSize) / (numberWalls + openingSize)
        util.create_long_wall (
            simctrl,
            roomCenterX + roomRadius * math.cos (angle),
            roomRadius * math.sin (angle), yaw = angle + math.pi / 2,
            color = common.WALL_COLOUR)
        angle = 2 * math.pi * (t + openingSize / 2) / (numberWalls + openingSize)
        util.create_long_wall (
            simctrl,
            -roomCenterX + roomRadius * math.cos (angle),
            roomRadius * math.sin (angle), yaw = angle + math.pi / 2,
            color = common.WALL_COLOUR)
    T = 13
    xl = -roomCenterX + roomRadius * math.cos (2 * math.pi * (-0.5 + openingSize / 2) / (numberWalls + openingSize))
    xh = roomCenterX + roomRadius * math.cos (2 * math.pi * (0.5 + numberWalls / 2 + openingSize) / (numberWalls + openingSize))
    yl = roomRadius * math.sin (2 * math.pi * (-0.5 + openingSize / 2) / (numberWalls + openingSize))
    yh = roomRadius * math.sin (-2 * math.pi * (-0.5 + openingSize / 2) / (numberWalls + openingSize))
    for t in range (0, T + 1):
        util.create_long_wall (
            simctrl,
            xl + t * (xh - xl) / T, yl,
            yaw = 0,
            color = common.WALL_COLOUR)
        util.create_long_wall (
            simctrl,
            xl + t * (xh - xl) / T, yh,
            yaw = 0,
            color = common.WALL_COLOUR)
            

def build_spots (simctrl):
    util.create_small_wall (
        simctrl,
        roomCenterX, roomCenterX / 2,
        math.pi / 4,
        color = common.SPOT_COLOUR)


# Parse command line arguments for number of fish
parser = argparse.ArgumentParser (
    description = 'A simulation environment with two rooms and several fish.')
parser.add_argument (
    '--number_fish',
    help = 'Number of fish to spawn',
    default = 10)
parser.add_argument (
    '--arena_radius',
    help = 'Arena radius',
    default = 50)
args = parser.parse_args ()

compute_room_specs (int (args.arena_radius))

simctrl = sim.Control()
build_rooms (simctrl)
build_spots (simctrl)
#spawn_control_fish (simctrl)
print 'Spawned', spawn_fish (simctrl, int (args.number_fish)), 'fish for a target of', args.number_fish
