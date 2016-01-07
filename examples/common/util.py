import math

def wrap_to_pi(angle):
    """
    Angle is in radians, in the interval [-2pi,2pi]
    """

    angle += 2* math.pi # We're in [0,4pi] now
    angle %= 2 * math.pi # Now we're between [0,2*pi]
    
    if angle > math.pi:
        angle -= 2 * math.pi

    return angle

WALL_HEIGHT = 5
wall_id = 1

def create_small_wall (simctrl, x, y, yaw, color):
    global wall_id
    simctrl.spawn (
        'Physical', 'Wall-{0}'.format (wall_id),
        (x, y, yaw),
        polygon = ((0.5, -0.5), (0.5, 0.5), (-.5, 0.5), (-.5, -.5)),
        color = color,
        height = WALL_HEIGHT)
    wall_id += 1

def create_long_wall (simctrl, x, y, yaw, color):
    global wall_id
    simctrl.spawn (
        'Physical', 'Wall-{0}'.format (wall_id),
        (x, y, yaw),
        polygon = ((1.5, -0.5), (1.5, 0.5), (-1.5, 0.5), (-1.5, -.5)),
        color = color,
        height = WALL_HEIGHT)
    wall_id += 1

def similar_colour (colour, target, epsilon = 0.1):
    r0, g0, b0 = colour
    r1, g1, b1 = target
    return math.fabs (r0 - r1) < epsilon \
       and math.fabs (g0 - g1) < epsilon \
       and math.fabs (b0 - b1) < epsilon
