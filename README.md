# <u> Drone Data Collection: </u>
NECESSARY CHANGES:
- [x] Change drone script to poll for a wifi connection when done collecting images
- [x] Images should be saved as jpegs on drone
- [x] When wifi connection is established, drone calls endpoint for each image to send over (instead of packaging all images into one POST payload)
- [x] Sockets will not be used anymore

Drone to server code can be found under `drone/data_collection`

`drone/data_collection/raspberry_pi.py` is the script that is run on the raspberry pi on the drone and captures RGB and IR images while it is doing its roundtrip. After completing its roundtrip, it will poll for a connection with the server and will send the new data once connected.

Server to db code can be found under `drone/server`

`drone/server/threshold_detect.py` is a preprocessing script that is designed to perform fire detection on the IR & RGB images classifying the severity levels of the fires detected if any.

`drone/server/uploadNewData.py` is a script that is constantly polling for a connection from the drone. Once connected, it will recieve the new data captured by the drone during its latest roundtrip and classify the data using our preprocessing script. After the preprocessing has been completed, this data will be sent to our backend server via POST request which will then add it to our MySQL (or POSTGRES) database.
