#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Python interface to simulated fish. """

import threading
import time

import zmq

from msg import dev_msgs_pb2
from msg import base_msgs_pb2


OBJECT_SIDE_RIGHT = 0 #: Sensor at 90°
"""
Right object sensor 
"""

OBJECT_RIGHT_FRONT = 1
"""
Right-front object sensor 
"""

OBJECT_FRONT = 2
"""
Front object sensor 
"""

OBJECT_LEFT_FRONT = 3
"""
Left-front object sensor 
"""

OBJECT_SIDE_LEFT = 4
"""
Left object sensor 
"""




LIGHT_SENSOR = 5
"""
Light sensor 
"""


LEFT_EYE = 6
"""
Camera image for left eye
"""

RIGHT_EYE = 7
"""
Camera image for right eye
"""



ARRAY = 10000
"""
Special value to get all sensor values from an array of sensors.
"""

class Fish:
    """ 
    The low-level interface to Fish 'robots'. 
    This class provides an api for programming fish behaviors.
    It creates a connection to the data source, i.e., the simulated fish.
    Waits for the fish of specified by 'name' to be spawned into the simulator.

    :param string rtc_file_name: Name of the run-time-configuration (RTC) file. This file specifies the simulation connection parameters and the name of the simulated fish object.
    :param string name: The name of the fish (if not specified in the RTC file).
    :param dict kwargs: accepts strings to override values for:
        `pub_addr` (defaults to localhost:5556)
        `sub_addr` (defautls to localhost:5555)

    """
    
    def __init__(self, rtc_file_name='', name = 'Fish', **kwargs):
        
        
        if rtc_file_name:
            # Parse the rtc file
            raise NotImplementedError("RTC file parsing for Fishes is not implemented yet. Please call the constructor with the name=fishname argument.")
        else:
            # parse any keywords provided, otherwise take default values
            self.__pub_addr = kwargs.get('pub_addr', 'tcp://127.0.0.1:5556')
            self.__sub_addr = kwargs.get('sub_addr', 'tcp://127.0.0.1:5555')
            self.__name = name
        
        self.__object_readings = dev_msgs_pb2.ObjectArray()
        self.__encoder_readings = dev_msgs_pb2.DiffDrive()
        self.__true_pose = base_msgs_pb2.PoseStamped()
        self.__vel_setpoints = dev_msgs_pb2.DiffDrive()
        self.__light_readings = base_msgs_pb2.ColorStamped()
        self.__color_setpoint = base_msgs_pb2.ColorStamped()
        self.__left_eye = dev_msgs_pb2.CircularCameraImage ()
        self.__right_eye = dev_msgs_pb2.CircularCameraImage ()

        # Create the data update thread
        self.__connected = False
        self.__context = zmq.Context(1)
        self.__comm_thread = threading.Thread(target=self.__update_readings)
        self.__comm_thread.daemon = True
        self.__lock =threading.Lock()
        self.__comm_thread.start()

        # Connect the publisher socket
        self.__pub = self.__context.socket(zmq.PUB)
        self.__pub.connect(self.__pub_addr)

        # Wait for the connection, check every second
        while not self.__connected:
            time.sleep(1)
        print('{0} connected!'.format(self.__name))

        # Wait one more second to get all the data
        time.sleep(0.5)

    def __update_readings(self):
        """ 
        Get a message from Fish and update data. 
        """
        self.__sub = self.__context.socket(zmq.SUB)
        self.__sub.connect(self.__sub_addr)
        self.__sub.setsockopt(zmq.SUBSCRIBE, self.__name)
                    
        while True:
            [name, dev, cmd, data] = self.__sub.recv_multipart()
            self.__connected = True
            
            ### Range readings ###
            if dev == 'Object':
                if cmd == 'Ranges':
                    # Protect write with a lock
                    # to make sure all data is written before access
                    with self.__lock:
                        self.__object_readings.ParseFromString(data)
                else:
                    print('Unknown command {0} for {1}'.format(cmd, self.__name))

            ### Base data ###
            elif dev == 'Base':
                if cmd == 'Enc':
                    with self.__lock:
                        self.__encoder_readings.ParseFromString(data)
                elif cmd == 'GroundTruth':
                    with self.__lock:
                        self.__true_pose.ParseFromString(data)
                elif cmd == 'VelRef':
                    with self.__lock:
                        self.__vel_setpoints.ParseFromString(data)
                else:
                    print('Unknown command {0} for Fish {1}'.format(cmd, self.__name))
            ### Light sensors ###
            elif dev == 'Light':
                if cmd == 'Readings':
                    with self.__lock:
                        self.__light_readings.ParseFromString(data)
                else:
                    print('Unknown command {0} for Fish {1}'.format(cmd, self.__name))

            ### Diagnostic color actuator ###
            elif dev == 'Color':
                if cmd == 'ColorVal':
                    with self.__lock:
                        self.__color_setpoint.ParseFromString(data)
                else:
                    print('Unknown command {0} for Fish {1}'.format(cmd, self.__name))

            ### Eye readings ###
            elif dev == 'Eye':
                if cmd == 'Left':
                    with self.__lock:
                        self.__left_eye.ParseFromString (data)
                elif cmd == 'Right':
                    with self.__lock:
                        self.__right_eye.ParseFromString (data)
                else:
                    print ('Unknown command {0} for Fish {1}'.format (cmd, self.__name))


    def get_range(self, id):
        """ 
        Returns the range reading corresponding to sensor id. 
        
        TODO: Fix the hacky correction of invalid readings
        """
        range = -1
        with self.__lock:
            if self.__object_readings.range:
                if id == ARRAY:
                    range = [val for val in self.__object_readings.range]
                else:
                    range = self.__object_readings.range[id-OBJECT_SIDE_RIGHT]

        # Hack to fix error of range 0.0 appearing
        # when no obstacles are present
        if range < 0.000001:
            range = 10

        return range

    def get_object_with_range(self, id):
        """
        Returns the (object,range) pair detected by sensor id.
        """
        r = -1
        obj = None
        with self.__lock:
            if self.__object_readings.range:
                if id == ARRAY:
                    r = [val for val in self.__object_readings.range]
                    for i in range(len(r)):
                        if r[i] < 0.000001:
                            r[i] = self.__object_readings.max_range
                    obj = [val for val in self.__object_readings.type]
                else:
                    r = self.__object_readings.range[id-OBJECT_SIDE_RIGHT]
                    # Hack to fix range 0.0 when no obstacle is present
                    if r < 0.000001:
                        r = self.__object_readings.max_range
                    obj = self.__object_readings.type[id-OBJECT_SIDE_RIGHT]

        return (obj,r)

    def get_light_rgb(self, id = LIGHT_SENSOR):
        """
        :return: (r,g,b) tuple, representing the light intensities at
                 red, green and blue wavelengths (currently, the sensor
                 reports only blue intensity, r and g are always 0).
        """
        with self.__lock:
            return (self.__light_readings.color.red,
                    self.__light_readings.color.green,
                    self.__light_readings.color.blue)


    def set_color(self,r=0.2,g=0.2,b=0.5):
        """
        Set the color of the fish. This can be useful for diagnostic and
        demonstration purposes.

        Take note of default values! E.g. in order to change the color to blue, 
        you have to call the function with all parameters explicitly set:

        b.set_color(r=0,g=0,b=1)

        To revert to "original" fish coloring, call the function without
        any parameters:

        b.set_color()

        :param float r: Red component intensity, between 0 and 1.
        :param float g: Green component intensity, between 0 and 1.
        :param float b: Blue component intensity, between 0 and 1.
        """

        # Limit values to [0,1] range
        r = sorted([0,r,1])[1]
        g = sorted([0,g,1])[1]
        b = sorted([0,b,1])[1]

        color = base_msgs_pb2.ColorStamped()
        color.color.red = r
        color.color.green = g
        color.color.blue = b

        self.__pub.send_multipart([self.__name,"Color","Set",color.SerializeToString()])
        

    def get_true_pose(self):
        """ 
        :return: (x,y,yaw) tuple, representing te true pose of the fish
                 in the world.
        """
        with self.__lock:
            return (self.__true_pose.pose.position.x,
                    self.__true_pose.pose.position.y,
                    self.__true_pose.pose.orientation.z)


    def set_vel(self, vel_left, vel_right):
        """ 
        Set wheel velocities. 

        Fish body velocities depend on wheel velocities in the following way:
        
        .. math:: v = \\frac{v_{left}+v_{right}}{2}
        .. math:: \\omega = \\frac{v_{right}-v_{left}}{d}

        where d is the distance between the wheels ("axle length").

        :param float vel_left: Left wheel velocity.
        :param float vel_right: Right wheel velocity.
        """
        vel = dev_msgs_pb2.DiffDrive();
        vel.vel_left = vel_left
        vel.vel_right = vel_right
        self.__pub.send_multipart([self.__name, "Base", "Vel",
                                   vel.SerializeToString()])


    def get_vel_ref(self):
        """
        :return: (vel_left,vel_right) tuple of wheel velocity setpoints.
        """
        return(self.__vel_setpoints.vel_left, 
               self.__vel_setpoints.vel_right)

    def get_color(self):
        """
        :return: (r,g,b) tuple of fish color setpoints.
        """
        return(self.__color_setpoint.color.red,
               self.__color_setpoint.color.green,
               self.__color_setpoint.color.blue)

    def get_eye (self, id):
        """
        :return: the image seen from one of the eyes
        """
        if id == LEFT_EYE:
            return self.__left_eye
        elif id == RIGHT_EYE:
            return self.__right_eye
