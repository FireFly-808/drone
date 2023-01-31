##########################################
# Data Collection Script for Raspberry Pi
##########################################

from datetime import datetime
import board
import busio
import numpy as np
import adafruit_mlx90640
import io
import socket
from picamera import PiCamera
import time


def encode_frame(frame):
    f = io.BytesIO()
    np.savez(f, frame=frame)
    
    packet_size = len(f.getvalue())
    header = '{0}:'.format(packet_size)
    header = bytes(header.encode())  # prepend length of array

    out = bytearray()
    out += header

    f.seek(0)
    out += f.read()
    return out

def send(frame, socket):
    if not isinstance(frame, np.ndarray):
        raise TypeError("input frame is not a valid numpy array")

    out = encode_frame(frame)

    try:
        socket.sendall(out)
    except BrokenPipeError:
        print("connection broken")
        raise

def load_gps(path):
    ''' Waypoint file format for parsing
        QGC WPL <VERSION>
        <INDEX> <CURRENT WP> <COORD FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/X/LATITUDE> <PARAM6/Y/LONGITUDE> <PARAM7/Z/ALTITUDE> <AUTOCONTINUE>
    '''
    file = open(path, "r")
    file.readline() # Read QGC, WPL <Version>
    file.readline() # Read home location information (not a waypoint)
    path_data = file.readlines() # path_data contains all the waypoints
    gps_coord = []
    
    # Parse GPS coordinates for all the waypoints
    for wayPoint in path_data:
        wayPoint = wayPoint.split('\t')
        gps_coord.append((wayPoint[8], wayPoint[9]))

    return gps_coord

# Return np array
def get_curr_gps():
    return np.array([0,0])


# Load GPS coordinates from mission planner.
gps_path = "data\path_planning\path_test.waypoints"
gps_coordinates = load_gps(gps_path)
num_pics = len(gps_coordinates)

# Instantiate sensor modules & communication protocol
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000) # setup I2C
mlx = adafruit_mlx90640.MLX90640(i2c) # begin MLX90640 with I2C comm
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ # set refresh rate
mlx_shape = (24,32)

camera = PiCamera()
camera.resolution = (720,480)
camera.start_preview()

server_addr = "192.168.10.43"
while(1):
    sensor_data = []
    gps_id = 0

    # Collect data
    while(len(sensor_data) < num_pics):
        curr_coord = get_curr_gps() # Current GPS position recieved over telemetary port from drone
        target_coord = gps_coordinates[gps_id]
        time.sleep(5)
        # Check to see if current position is within range of next waypoint
        # if abs(curr_coord[0] - target_coord[0]) < 1.5 and abs(curr_coord[1] - target_coord[1]) < 1.5:
        try:
            curr_time = np.array([datetime.now()])
            frame = np.zeros((24*32))
            mlx.getFrame(frame)
            ir_data = (np.reshape(frame,mlx_shape))

            # Get image data as numpy array
            img_data = np.empty((480*720*3), dtype=np.uint8)
            camera.capture(img_data, 'bgr')
            img_data = np.reshape(img_data, (480,720,3))
            
            sensor_data.append((ir_data, img_data, curr_coord, curr_time))
            gps_id += 1

        except ValueError:
            pass
    
    # Poll for socket connection
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while (1):
        try:
            clientSocket.connect((server_addr, 2022))
            break
        except Exception as e:
            pass

    # Send sensor data to server
    for frame in sensor_data:
        for data in frame:
            send(data, clientSocket)
    
    # Close socket connection
    clientSocket.close()