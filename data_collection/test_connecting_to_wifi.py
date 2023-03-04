import requests
import time

SERVER_URL = 'http://ec2-3-219-240-142.compute-1.amazonaws.com'

REGISTER_PATH_URL_PROD = SERVER_URL+'/api/server/paths/'

def wait_for_connection():
    i = 0
    while True:
        try:
            print(f"connection attemp #{i}")
            i += 1
            res = requests.post(REGISTER_PATH_URL_PROD, {'name':'daniels crib'})
            print("WIFI KANEKSHAN ESTABLISHED")
            break
        except requests.exceptions.RequestException:
            time.sleep(1)
            
    path_id = res.json()['id']
    print(f"path_id:{path_id}")

wait_for_connection()