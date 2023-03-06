##########################################
# Data Collection Script for Raspberry Pi
##########################################

from datetime import datetime
import numpy as np
import io
import time
import requests
from PIL import Image
import pickle
import os

DEBUG = False

SERVER_URL = 'http://ec2-3-219-240-142.compute-1.amazonaws.com'

REGISTER_PATH_URL_LOCALHOST = 'http://127.0.0.1:8000/api/server/paths/'
REGISTER_PATH_URL_PROD = SERVER_URL+'/api/server/paths/'

ADD_RECORD_URL_LOCALHOST = 'http://127.0.0.1:8000/api/server/add_record/'
ADD_RECORD_URL_PROD = SERVER_URL+'/api/server/add_record/'

PATHNAME = 'waterloo campus'

# imports for raspberry pi
if not DEBUG:
    import busio
    import adafruit_mlx90640
    from picamera import PiCamera
    import board
    from dronekit import connect, VehicleMode
    import RPi.GPIO as GPIO

class DataCollector:

    def __init__(self):
        # Load GPS coordinates from mission planner.
        ##### CURRENTLY MUST MANUALLY UPDATE WITH FILENAME BEFORE EACH MISSION 
        if not DEBUG:
            self.gps_path = "./path_planning/path_test.waypoints"
            # Serial port on rpi
            connection_string = '/dev/serial0'
            self.drone = connect(connection_string, wait_ready=True, baud=57600)
        else:
            self.gps_path = "..\path_planning\path_test.waypoints"
        
        self.gps_coordinates = self.load_gps(self.gps_path)
        self.num_pics = len(self.gps_coordinates)

        self.setupSensors()
        self.flightDataCollection()

    def setupSensors(self):
        # Instantiate sensor modules & communication protocol
        if not DEBUG:
            #Trigger from Pixhawk on GPIO 4
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(4, GPIO.IN)

            i2c = busio.I2C(board.SCL, board.SDA, frequency=400000) # setup I2C
            self.mlx = adafruit_mlx90640.MLX90640(i2c) # begin MLX90640 with I2C comm
            self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ # set refresh rate
            self.camera = PiCamera()
            self.camera.resolution = (1280,720)
            self.camera.start_preview()
            
        self.mlx_shape = (24,32)
        self.camera_shape = (720,1280,3)

    def temps_to_rescaled_uints(self, raw_np_image):
        #Function to convert temperatures to pixels on image
        # Fix dead pixel
        raw_np_image[6][0] = int((raw_np_image[6][1] + raw_np_image[5][0] + raw_np_image[7][0]) / 3)

        # Just in case there are any NaNs
        raw_np_image = np.nan_to_num(raw_np_image)

        _temp_min = np.min(raw_np_image)
        _temp_max = np.max(raw_np_image)
        norm = np.uint8((raw_np_image - _temp_min)*255/(_temp_max-_temp_min))

        norm.shape = self.mlx_shape
        return norm

    def load_gps(self, path):
        ''' Waypoint file format for parsing
            QGC WPL <VERSION>
            <INDEX> <CURRENT WP> <COORD FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/X/LATITUDE> <PARAM6/Y/LONGITUDE> <PARAM7/Z/ALTITUDE> <AUTOCONTINUE>
        '''
        file = open(path, "r")
        file.readline() # Read QGC, WPL <Version>
        file.readline() # Read home location information (not a waypoint)
        path_data = file.readlines() # path_data contains all the waypoints
        gps_coord = []
        
        # Parse GPS coordinates for all the waypoints, skipping any 0.0 (non coordinate instructions)
        for wayPoint in path_data:
            wayPoint = wayPoint.split('\t')
            if float(wayPoint[8]) != 0 or float(wayPoint[9]) != 0:
                gps_coord.append((wayPoint[8], wayPoint[9]))

        return gps_coord

    def get_curr_gps(self):
        if DEBUG:
            return np.array([0,0])
        else:
            return [self.drone.location.global_frame.lat, self.drone.location.global_frame.lon]

    
    def flightDataCollection(self):
        while(True):
            sensor_data = self.collectPhotos()

            #Save the data as pickle file in case of upload fail
            #May not be the best option for large datasets
            with open('data.pickle', 'wb') as file:
                pickle.dump(sensor_data, file)

            while(True):
                # print("trying to connect")
                res = os.system('ping google.com')
                if not res:
                    break
                time.sleep(1)

            # print("connected")
            
            res = requests.post(REGISTER_PATH_URL_PROD, {'name':PATHNAME})
            path_id = res.json()['id']

            self.sendData(sensor_data, path_id)

            # ONE FLIGHT
            break

        
    def collectPhotos(self):
        sensor_data = []
        gps_id = 0

        # Collect data
        while(len(sensor_data) < self.num_pics if not DEBUG else 3):
            curr_coord = self.get_curr_gps() # Current GPS position recieved over telemetary port from drone
            if DEBUG:
                target_coord = [0,0]
            else:
                target_coord = self.gps_coordinates[gps_id]
            
            # If receive trigger from Pixhawk, coordinate reached
            if GPIO.input(4):
                try:
                    curr_time = np.array([datetime.now()])
                    
                    if DEBUG:
                        frame = np.random.uniform(-20.0, 200.0, 32*24)
                    else:
                        frame = np.zeros((24*32))
                        self.mlx.getFrame(frame)                    

                    if DEBUG:
                        img_data = np.random.uniform(-20.0, 200.0, 320*240*3)
                    else:
                        img_data = np.empty((720*1280*3), dtype=np.uint8)
                        self.camera.capture(img_data, 'rgb')
                    
                    img_data = np.reshape(img_data, self.camera_shape)
                    ir_data = np.reshape(frame, self.mlx_shape)
                    sensor_data.append((ir_data, img_data, curr_coord, curr_time))
                    gps_id += 1

                except ValueError:
                    pass
                
                #if still high wait for it to go low again
                startTime = time.time()
                while(1): 
                    if GPIO.input(4):
                        startTime = time.time()
                    elif time.time() - startTime > 1:
                        break


        return sensor_data

    def sendData(self, sensor_data, path_id):
        for frame in sensor_data:
            
            lat = frame[2][0]
            lon = frame[2][1]
            date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

            # create the payload data with the image data
            #first must normalize the ir data
            ir_norm = self.temps_to_rescaled_uints(frame[0])
            img_ir = Image.fromarray(ir_norm, mode="L")
            img_rgb = Image.fromarray(frame[1], mode="RGB")

            buffer_ir = io.BytesIO()
            buffer_rgb = io.BytesIO()
            
            img_ir.save(buffer_ir, format='PNG')
            img_rgb.save(buffer_rgb, format='PNG')

            ir_image_file = ("image_ir.png", buffer_ir.getvalue())
            rgb_image_file = ("image_rgb.png", buffer_rgb.getvalue())

            # create the payload data with the image data
            data = {
                "lon": lon,
                "lat": lat,
                "path_id": path_id,
                "date": date,
            }
            files = {
                "image_ir": ir_image_file,
                "image_rgb": rgb_image_file,
            }

            # make the POST request with the payload
            res = requests.post(ADD_RECORD_URL_PROD, data=data, files=files)
            if res.status_code == 500:
                with open("failed_images_log.txt", "a") as f:
                    entry = str(res.json())
                    f.write(entry + "\n")
                    f.close()


if __name__ == "__main__":
    dc = DataCollector()
