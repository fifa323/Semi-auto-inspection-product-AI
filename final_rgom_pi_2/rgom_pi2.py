# PI2
import configparser
import cv2
import numpy as np
import os
import socket
import sys
import threading
import time
import queue

# State machine
IDLE = "idle"
EMERGENCY = "emergency"

# Variable
state = IDLE

# Queue
cam_q = queue.Queue()

config = configparser.ConfigParser()
config.read("config.ini")

# Server config
SERVER_IP = config.get("SERVER", "IP")
SERVER_PORT = config.getint("SERVER", "PORT")

# PI config
PI1_IP = config.get("RASPBERRY_PI", "PI_1_IP")
PI1_PORT = config.getint("RASPBERRY_PI", "PI_1_PORT")
PI2_PORT = config.getint("RASPBERRY_PI", "PI_2_PORT")

# Camera config
WIDTH_4K = config.getint('CAMERA','WIDTH_4K')
HEIGHT_4K = config.getint('CAMERA','HEIGHT_4K')
CAMERA_INDEX = config.getint('CAMERA','CAMERA_INDEX')

# Variable config
SEND_MVP = config.get('VARIABLE','SEND_MVP').encode().decode('unicode_escape').encode()

# Share folder config.
MOUNT_NAME = config.get("SHARE_FOLDER", "MOUNT_NAME")
COM_IP = config.get("SHARE_FOLDER", "COM_IP")
FOLDER_NAME = config.get("SHARE_FOLDER", "FOLDER_NAME")
USERNAME = config.get("SHARE_FOLDER", "USERNAME")
PASSWORD = config.get("SHARE_FOLDER", "PASSWORD")
DOMAIN = config.get("SHARE_FOLDER", "DOMAIN", fallback="")

# Mount folder share
def check_mount():
    if os.path.ismount(MOUNT_NAME):
        os.system(f"sudo umount {MOUNT_NAME}")

    mount_cmd = f"sudo mount -t cifs //{COM_IP}/{FOLDER_NAME} {MOUNT_NAME} -o rw,uid=pi,gid=pi,username={USERNAME},password={PASSWORD}"

    if DOMAIN:
        mount_cmd += f",domain={DOMAIN}"
    os.system(mount_cmd)

    if os.path.ismount(MOUNT_NAME):
        pass
    else:
        print("Failed to mount.")
        sys.exit(1)
        
def recv_pi1():
    global state
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", PI2_PORT))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            print(f"Connected to PI1: {addr}")
            with conn:
                    data = conn.recv(1024).decode().strip()
                    print(f"Received from PI1: {data}")
                    if not data:
                        break
                    elif data == 'start':
                        cam_q.put(data)
                    elif data == 'send':
                        send_mvp()
                    elif data == 'capture':
                        test_capture()
                    elif data == 'emergency':
                        state = EMERGENCY
                    elif data == 'release':
                        reset_system()
                 
def send_mvp():
    global state
    if state == EMERGENCY:
        print('Emergency, Stop sending to MVP')
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(SEND_MVP)
        print(f'send {SEND_MVP}')
        s.close()

def reset_system():
    global state, rnd
    state = IDLE
    print('RELEASED.')

def camera_thd():
    global rnd, filename, frame
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH_4K)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT_4K)
        
    while True:
        try:
            camera = cam_q.get(timeout=0.1)
        except queue.Empty:
            camera = None
                
        if camera is None:
            cap.grab()
            continue
            
        time.sleep(0.1)
        ret, frame = cap.read()
        if not ret:
            print('Camera read failed.')
            cap.release()
            break
            
        filename = os.path.join(MOUNT_NAME, "img.jpg")
        cv2.imwrite(filename, frame)
        # print(f'img_{camera} saved.')
        # time.sleep(0.1)
        # send_mvp()
            
def test_capture():
    global frame
    test_2_path = os.path.join(MOUNT_NAME,'img_test_2.jpg')
    cv2.imwrite(test_2_path, frame)

threading.Thread(target=recv_pi1, daemon= True).start()
threading.Thread(target=camera_thd, daemon=True).start()

check_mount()
print("PI2 Ready ....... to START !")
try:
    while True:
        pass   
except KeyboardInterrupt:
    pass
finally:
    print("EXIT program.")
