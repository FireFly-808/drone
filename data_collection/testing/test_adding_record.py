import requests
from datetime import datetime
import numpy as np
from PIL import Image
import tempfile
import io

SERVER_URL = 'http://ec2-3-219-240-142.compute-1.amazonaws.com'

REGISTER_PATH_URL_PROD = SERVER_URL+'/api/server/paths/'

ADD_RECORD_URL_LOCALHOST = 'http://127.0.0.1:8000/api/server/add_record/'
ADD_RECORD_URL_PROD = SERVER_URL+'/api/server/add_record/'

def registerPath(pathname='zimbabwe'):
    res = requests.post(REGISTER_PATH_URL_PROD, {'name':pathname})

def sendDataPost(path_id):
    date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    with tempfile.NamedTemporaryFile(suffix='.png') as file1:
        with tempfile.NamedTemporaryFile(suffix='.png') as file2:
            img_data = np.random.uniform(-20.0, 200.0, 320*240*3)
            img_data = np.reshape(img_data, (240,320,3))
            im1 = Image.fromarray(img_data, "RGB")
            im2 = Image.fromarray(img_data, "RGB")
            # im1 = Image.new('RGB',(10,10))
            # im2 = Image.new('RGB',(10,10))
            im1.save(file1, format='PNG')
            im2.save(file2, format='PNG')
            file1.seek(0)
            file2.seek(0)

            # create the payload data with the image data
            data = {
                "lon": 1.1,
                "lat": 2.2,
                "path_id": path_id,
                "date": '2000-02-14T18:00:00Z',
            }
            files = {
                "image_ir": file1,
                "image_rgb": file2,
            }

            # make the POST request with the payload
            res = requests.post(ADD_RECORD_URL_LOCALHOST, data=data, files=files)
            print(res)


def sendDataPostNoSave(path_id):
    date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    img_data = np.random.uniform(-20.0, 200.0, 320*240*3)
    img_data = np.reshape(img_data, (240,320,3))
    png = Image.fromarray(img_data, mode="RGB")
    buffer = io.BytesIO()
    
    png.save(buffer, format='PNG')

    image_file = ("image.png", buffer.getvalue())

    # create the payload data with the image data
    data = {
        "lon": 132.1,
        "lat": 2543.2,
        "path_id": path_id,
        "date": '2000-02-14T18:00:00Z',
    }
    files = {
        "image_ir": ("image.png", buffer.getvalue()),
        "image_rgb": ("image.png", buffer.getvalue()),
    }

    # make the POST request with the payload
    res = requests.post(ADD_RECORD_URL_LOCALHOST, data=data, files=files)
    print(res)
    
def sendDataPost2image(lat, lon, path_id, ir_image_data, rgb_image_data):
    date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    img_ir = Image.fromarray(ir_image_data, mode="L")
    img_rgb = Image.fromarray(rgb_image_data, mode="RGB")

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
    print(res.json()['id'])
    print(res.status_code)
    if True:
        with open("failed_images_log.txt", "a") as f:
            entry = str(res.json())
            f.write(entry + "\n")
            f.close()


# make image
mlx_shape = (24,32)
camera_shape = (240,320,3)

rgb = np.random.uniform(-20.0, 200.0, 320*240*3)
ir = np.random.uniform(-20.0, 200.0, 32*24)
rgb_data = np.reshape(rgb, camera_shape)
ir_data = np.reshape(ir, mlx_shape)

# path_id = registerPath('umars crib')
# sendDataPost(path_id)
# sendDataPostNoSave(path_id)
path_id = 1
sendDataPost2image(888, 901, path_id, ir_data, rgb_data)