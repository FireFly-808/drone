import re
from xml.sax.handler import property_encoding
import pandas as pd
import socket
import numpy as np
from io import BytesIO
import logging
import io
from PIL import Image
import datetime
import os
from pathlib import Path

from db_util import create_db_connection, execute_query, read_query, getFlightNum
from threshold_detect import detect_fires


DEBUG = 0


class DataUploader:
    def __init__(self):
        self.server_addr = "192.168.10.43"
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_addr = 0
        self.client_conn = 0
        self.socket_buffer_size = 1024
        self.mlx_shape = (32, 24)
        self.rgb_shape = (240, 320, 3)
        self.frameCount = 1

        self.frameBuffer = bytearray()
        self.states = ["ir", "rgb", "gps", "time"]
        self.currState = 0

        self.allData = []
        self.tempList = []

        self.rgb_folder_path = r"..\server_hd\rgb_images"
        self.ir_folder_path = r"..\server_hd\ir_images"

        Path(self.rgb_folder_path).mkdir(parents=True, exist_ok=True)
        Path(self.ir_folder_path).mkdir(parents=True, exist_ok=True)

        self.flightNum = 1

        self.pw = "superwoofer123"
        if not DEBUG:
            self.sqlConn = create_db_connection(
                "localhost", "root", self.pw, "firefly_db"
            )
            self.flightNum = getFlightNum(self.sqlConn)

        print(f"flight num: {self.flightNum}")

        self.startServer()
        self.acceptDroneConnections()

    def startServer(self):
        host=socket.gethostname()
        # host = "127.0.0.1"
        # host = "192.168.10.43"
        ip = socket.gethostbyname(host)
        print(ip)
        port = 2022

        self.main_socket.bind((host, port))
        self.main_socket.listen()

    def acceptDroneConnections(self):
        acceptedCount = 1
        while True:
            print("waiting for a connection")
            self.client_conn, self.client_addr = self.main_socket.accept()
            print(f"connected to: {self.client_addr[0]}")

            while True:
                self.receiveFrame()
                if self.closeSocketFlag:
                    self.frameBuffer = bytearray()
                    break

            acceptedCount += 1

            # DEBUGING - REMOVE BREAK
            if acceptedCount > 5:
                break

    def receiveFrame(self):
        bufferToProcess = None
        length = None
        self.closeSocketFlag = False

        while True:
            data = self.client_conn.recv(self.socket_buffer_size)
            if self.frameBuffer == b"e":
                self.closeSocketFlag = True
                self.flightNum += 1
                return

            self.frameBuffer += data

            if length and len(self.frameBuffer) >= length:
                # if full frame received truncate and proceed to processing
                bufferToProcess = self.frameBuffer[:length]
                self.frameBuffer = self.frameBuffer[length:]
                # print("received full frame... breaking out")
                break

            if length is None:
                # havent gotten a packet yet
                if b":" in self.frameBuffer:
                    # this packet is the first one in the msg
                    # remove the length bytes from the front of frameBuffer
                    # leave any remaining bytes in the frameBuffer!
                    length_str, _, self.frameBuffer = self.frameBuffer.partition(b":")
                    length = int(length_str)
                    print(f"length of {self.states[self.currState]}: {length}")

                    # the message is entirely in this packet, therefore cut off remaining bytes
                    if len(self.frameBuffer) > length:
                        # split off the full message from the remaining bytes
                        # leave any remaining bytes in the frameBuffer!
                        bufferToProcess = self.frameBuffer[:length]
                        self.frameBuffer = self.frameBuffer[length:]
                        self.length = None
                        # break out of receiving loop and start processing
                        # print("frame smaller than buffer")
                        break
                else:
                    # print(len(self.frameBuffer))
                    continue

        # print(f"final length of frameBuffer: {len(bufferToProcess)}")
        frame = np.load(io.BytesIO(bufferToProcess), allow_pickle=True)["frame"]
        self.saveFrame(frame)

    def saveFrame(self, frame):
        print(f"processed incoming frame #{self.frameCount}")
        print(f"{self.states[self.currState]} frame received")
        print("")

        self.tempList.append(frame)

        if self.currState == 3:
            self.processData(self.tempList)
            self.allData.append(self.tempList)
            self.tempList = []
            print(f"size of alldata : {len(self.allData)}")
            print("===============================================")

        self.currState = (self.currState + 1) % 4
        self.frameCount += 1

    def processData(self, dataList):
        print(f"processing frame #{self.frameCount}")
        irRaw, rgbRaw, gpsRaw, timeRaw = dataList
        # ir_data = (np.reshape(irRaw, self.mlx_shape))
        # rgb_data = (np.reshape(rgbRaw, self.rgb_shape))
        lon = gpsRaw[0]
        lat = gpsRaw[1]
        datetime_object = timeRaw[0]
        date = datetime_object.strftime("%d-%m-%Y")
        gps_time_part = f"{lon}_{lat}__{date}"

        # save ir and rgb images as PNGs
        ir_file_path = self.saveArrToPNG(irRaw, gps_time_part, type="ir")
        rgb_file_path = self.saveArrToPNG(rgbRaw, gps_time_part, type="rgb")

        size = detect_fires(irRaw)

        if not DEBUG:
            self.appendEntryToDB(
                lon.astype(float),
                lat.astype(float),
                datetime_object,
                str(ir_file_path),
                str(rgb_file_path),
                size,
            )

    def saveArrToPNG(self, rawData, extension, type):
        file_name = f"{type}_{extension}.png"
        file_path = os.path.join("..", "server_hd", f"{type}_images", file_name)
        im = Image.fromarray(rawData, "L" if type == "ir" else "RGB")
        im.save(file_path)
        print(f"saved {type} as png")
        return file_path

    def appendEntryToDB(self, lon, lat, date, ir_path, rgb_path, size=-1):
        print("adding entry to db")

        # check if location exists in locations table
        query_checkLoc = "SELECT locID FROM locations WHERE lon = %s and lat = %s;"
        params_checkLoc = (lon, lat)
        result = read_query(self.sqlConn, query_checkLoc, params_checkLoc)

        # if location does not exist
        if not result:
            # make a location record
            query_addLoc = "INSERT INTO locations (lon, lat) VALUES (%s, %s);"
            params_addLoc = (lon, lat)
            execute_query(self.sqlConn, query_addLoc, params_addLoc)
            result = read_query(self.sqlConn, query_checkLoc, params_checkLoc)

        locID = result[0][0]

        # add image record to db
        query_addImageRecord = "INSERT INTO image_records (locID, flightNum, date_time, irImagePath, rgbImagePath) VALUES (%s, %s, %s, %s, %s);"
        params_addImageRecord = (locID, self.flightNum, date, ir_path, rgb_path)
        execute_query(self.sqlConn, query_addImageRecord, params_addImageRecord)

        # if image contains a hotspot record a hotspot
        if size > 0:
            query_addHS = "INSERT INTO hotspots (locID, flightNum, size, hotspot_status) VALUES (%s, %s, %s, %s);"
            params_addHS = (locID, self.flightNum, size, 0)
            execute_query(self.sqlConn, query_addHS, params_addHS)


d1 = DataUploader()