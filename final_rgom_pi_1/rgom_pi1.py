#PI1
import ast
import configparser
import cv2
import socket
import sys
import threading
import queue
import time
import numpy as np
import os
import warnings
from datetime import datetime
from gpiozero import Button,LED
from ezyrobo import EZRobo

#warnings.filterwarnings("ignore", category=RuntimeWarning, module="gpiozero")
#sys.stderr = open(os.devnull, 'w')

# State machine
IDLE = "idle"
INSPECT = "inspect"
EMERGENCY = "emergency"
FINISH = "finish"
PROCESS = 'processing'
RESET = 'reset'

# Variable
rnd = 0
state = IDLE
ch_pressed = None
new_data = []
new_data_1 = []
new_data_2 = []

# State flags
confirm_ng = False

E = EZRobo()
origin_step = [0, 0, 0]

# GPIO buttons (PI1)
bt_start_1 = Button(23, hold_time=0.1, pull_up=False)
bt_start_2 = Button(24, hold_time=0.1, pull_up=False)
bt_reset = Button(25, hold_time=0.1, pull_up=False)
bt_confirm_ok = Button(16, hold_time=0.1, pull_up=False)
bt_confirm_ng = Button(20, hold_time=0.1, pull_up=False)
bt_emergency = Button(12, hold_time=0.1, pull_up=False)
bt_ng_box_reset = Button(21, hold_time=0.1, pull_up=False)
ok_box = LED(5)
ng_box = LED(6)

# Queue
robo_q = queue.Queue()
cam_q = queue.Queue()
mvp_res_q =queue.Queue()

config = configparser.ConfigParser()
config.read("config.ini")

# Server config
SERVER_IP = config.get("SERVER", "IP")
SERVER_PORT = config.getint("SERVER", "PORT")

# PI config
PI2_IP = config.get("RASPBERRY_PI", "PI_2_IP")
PI1_PORT = config.getint("RASPBERRY_PI", "PI_1_PORT")
PI2_PORT = config.getint("RASPBERRY_PI", "PI_2_PORT")

# Camera config
WIDTH_4K = config.getint('CAMERA','WIDTH_4K')
HEIGHT_4K = config.getint('CAMERA','HEIGHT_4K')
WIDTH = config.getint('CAMERA','WIDTH')
HEIGHT = config.getint('CAMERA','HEIGHT')
CAMERA_INDEX = config.getint('CAMERA','CAMERA_INDEX')

# Variable config
STEPS_STR = config.get('VARIABLE', 'STEPS')
steps = ast.literal_eval(STEPS_STR)
SEND_MVP = config.get('VARIABLE','SEND_MVP').encode().decode('unicode_escape').encode()

# Share folder config.
MOUNT_NAME = config.get("SHARE_FOLDER", "MOUNT_NAME")
COM_IP = config.get("SHARE_FOLDER", "COM_IP")
FOLDER_NAME = config.get("SHARE_FOLDER", "FOLDER_NAME")
FOLDER_NAME_1 = config.get("SHARE_FOLDER", "FOLDER_NAME_1")
FOLDER_NAME_2 = config.get("SHARE_FOLDER", "FOLDER_NAME_2")
USERNAME = config.get("SHARE_FOLDER", "USERNAME")
PASSWORD = config.get("SHARE_FOLDER", "PASSWORD")
DOMAIN = config.get("SHARE_FOLDER", "DOMAIN", fallback="")
# for save img when response ng
FOLDER_OK = config.get("SHARE_FOLDER", "SUB_FOLDER_1")
FOLDER_NG = config.get("SHARE_FOLDER", "SUB_FOLDER_2")

# Screen config
green_screen = np.full((HEIGHT, WIDTH, 3), (0, 255, 0), np.uint8)
red_screen = np.full((HEIGHT, WIDTH, 3), (0, 0, 255), np.uint8)
grey_screen = np.full((HEIGHT, WIDTH, 3), 128, dtype=np.uint8)
yellow_screen = np.full((HEIGHT, WIDTH, 3), (0, 255, 255), np.uint8)

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
                    
def send_pi2(msg):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((PI2_IP, PI2_PORT))
        s.sendall(msg.encode())
        # print('send', msg)
     
def recv_mvp():
    global state
    if state == EMERGENCY:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 9000))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            print(f"Connected to MVP: {addr}")
            with conn:
                data = conn.recv(1024).decode().strip()
                print(f"Received from MVP: {data}")
                if data:
                    read_data(data)
                    send_pi2('send')

def recv_mvp_2():
    global state
    if state == EMERGENCY:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 9001))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            print(f"Connected to MVP2: {addr}")
            with conn:
                data = conn.recv(1024).decode().strip()
                print(f"Received from MVP2: {data}")
                if data:
                    read_data(data)
                    
def send_mvp():
    global state
    if state == EMERGENCY:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(SEND_MVP)
        s.close()
    
def read_data(data_recv):
    global new_data_1, new_data_2
    data_set = data_recv.strip().splitlines()
    
    for i in data_set:
        if not i:
            continue

        label, values = i.split(",")
        pos = values.split("_")
        
        xy_position = []
        prev_x, prev_y = None, None
        
        for i in range(0, len(pos), 2):
            x = float(pos[i])
            y = float(pos[i+1])
            
            if x == 0.00 and y == 0.00:
                continue
            
            if (prev_x and prev_y ) is not None:
                if abs(x - prev_x) <= 200 and abs(y - prev_y) <= 200:
                    continue

            xy_position.extend([x, y])
            prev_x, prev_y = x, y 
            
        new_data.append([label] + xy_position)

    if len(new_data) == 2:
        new_data_1 = new_data[0]
        new_data_2 = new_data[1]
        mvp_res_q.put(new_data)
        
    else:
        print("Waiting response 'P2' from MVP.")
        
def check_key():
    cv2.namedWindow('ezyrobo')
    global state, ch_pressed, confirm_ng
    step_list = {
        '0': lambda: (E.move(origin_step), E.toOrigin(), print('ORIGIN.')),
        '1': lambda: (E.move(steps[0]), print(steps[0])),
        '2': lambda: (E.move(steps[1]), print(steps[1])),
        '3': lambda: (E.move(steps[2]), print(steps[2])),
    }
    
    while True:
        ch = 0xff & cv2.waitKey(30)
        if ch == -1:
            continue
        key = chr(ch)
        
        if key == 's' and not confirm_ng:
            state = INSPECT
        elif key == 'a':
            test_capture()
        elif key == 'q':
            cv2.destroyWindow('Test')   
        elif key == 'c':
            ch_pressed = 'c'
        elif key == 'z':
            ch_pressed = 'z'
        elif key == 'n':
            ch_pressed = 'n'
        elif key in step_list:
            step_list[key]()
            print(f'{key} pressed.') 
            continue
        else:
            continue
        print(f'{key} pressed.')

def test_capture():
    test_1_path = os.path.join(MOUNT_NAME,"img_test_1.jpg")
    cv2.imwrite(test_1_path, frame)
    send_pi2('capture')
    time.sleep(0.5)
    test_2_path = os.path.join(MOUNT_NAME,"img_test_2.jpg")
            
    if test_1_path and os.path.exists(test_1_path):
        test_1_img = cv2.imread(test_1_path)
                
    if test_2_path and os.path.exists(test_2_path):
        test_2_img = cv2.imread(test_2_path)
            
    resize_test_1 = cv2.resize(test_1_img,(WIDTH,HEIGHT))
    resize_test_2 = cv2.resize(test_2_img,(WIDTH,HEIGHT))
            
    combined = np.hstack((resize_test_1, resize_test_2))
    cv2.imshow('Test', combined)
    cv2.waitKey(1)
           
def check_twohands_switch():
    if bt_start_1.is_held and bt_start_2.is_held:
        held_time1 = bt_start_1.held_time
        held_time2 = bt_start_2.held_time
        delta = abs(held_time1 - held_time2)
        # print("delta", delta)
        if delta <= 0.5:
            return True
        else:
            return False

def check_state():
    global state, rnd, ch_pressed, new_data, confirm_ng
    while True:
        if state != EMERGENCY and bt_emergency.is_held:
            state = EMERGENCY
            robo_q.queue.clear()
            mvp_res_q.queue.clear()
            new_data.clear()
            send_pi2('emergency')
            print('EMERGENCY PRESSED.')
            
        elif state == EMERGENCY:
            bt_emergency.wait_for_release()
            print('EMERGENCY RELEASED.')
            try:
                cv2.destroyWindow('ezyroboNG')
            except cv2.error:
                pass
            send_pi2('release')
            state = RESET
            
        elif state == IDLE:
            if confirm_ng:
                if ch_pressed == 'n' or bt_ng_box_reset.is_held:
                    ng_box.off()
                    print('ng_box is off')
                    confirm_ng = False
                    ch_pressed = None
                else:
                    continue
                
            ret = check_twohands_switch()
            if ret is None:
                continue
            if ret:
                state = INSPECT
            else:
                state = RESET
            
        elif state == INSPECT and not ok_box.is_lit and not ng_box.is_lit:
            robo_q.queue.clear()
            if rnd == 0:
                for i in steps:
                    robo_q.put(i)
                state = PROCESS

        elif state == FINISH:
            robo_q.queue.clear()
            rnd = 0
            state = IDLE
            E.move(origin_step)
            E.toOrigin()
            print('FINISHED.')
            if confirm_ng:
                ng_box.on()
                print('ng box is on')
            else:
                ok_box.on()
                print('ok box is on')
                time.sleep(3)
                ok_box.off()
                print('ok box is off')
                            
        elif state == RESET:
            reset_display()
            while not bt_reset.is_held:
                time.sleep(0.1)
            bt_reset.wait_for_press()
            reset_system()

def screen_display(img_screen, text, text_index=0, max_index=0):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_color = 0  # black
    padding = 20
    img_h, img_w = img_screen.shape[:2]

    if text == 'ROUND':
        label_text = f'{text} {rnd + 1} defects {text_index}/{max_index}'
    else:
        label_text = text

    def get_optimal_font_params(text, img_w, img_h, max_fraction=0.8):
        for scale in reversed([i * 0.1 for i in range(1, 101)]):
            thickness = max(5, int(scale * 1.5))
            (text_w, text_h), baseline = cv2.getTextSize(text, font, scale, thickness)
            if text_w < img_w * max_fraction and text_h < img_h * max_fraction:
                return scale, thickness
        #If long text or small image
        return 0.5, 1  

    font_scale, font_thickness = get_optimal_font_params(label_text, img_w, img_h)

    (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, font_thickness)

    if text == 'ROUND':
        x = padding
        y = padding + text_height
        rect_top_left = (x - padding, y - text_height - padding)
        rect_bottom_right = (x + text_width + padding, y + baseline + padding)

        overlay = img_screen.copy()
        cv2.rectangle(overlay, rect_top_left, rect_bottom_right, (255, 255, 255), -1)
        alpha = 0.6
        cv2.addWeighted(overlay, alpha, img_screen, 1 - alpha, 0, img_screen)

        cv2.putText(img_screen, label_text, (x, y), font, font_scale, text_color, font_thickness)
    else:
        x = (img_w - text_width) // 2
        y = (img_h + text_height) // 2
        cv2.putText(img_screen, label_text, (x, y), font, font_scale, text_color, font_thickness)

    return img_screen
    
def reset_display():
    reset_screen = screen_display(red_screen.copy(), 'Please reset.')
    cv2.imshow('reset', cv2.resize(reset_screen, (WIDTH, HEIGHT)))
    cv2.waitKey(1)
    
def reset_system():
    global state, rnd
    print("Resetting...")
    cv2.destroyWindow("reset")
    state = IDLE
    rnd = 0
    E.move(origin_step)
    E.toOrigin()
    print("ORIGIN.")
  
def camera_thd():
    global rnd, filename_1, frame
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH_4K)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT_4K)
        
    while True:
        try:
            camera = cam_q.get(timeout=0.1)
            new_data.clear()
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
            
        filename_1 = os.path.join(MOUNT_NAME, FOLDER_NAME_1, "img.jpg")
        cv2.imwrite(filename_1, frame)
        # print(f'img_{camera} saved.')
        time.sleep(0.1)
        send_mvp()
    
def ng_image_display(image_1, image_2, index, data=None, draw_p1=True, draw_p2=True):
    error_screen = screen_display(red_screen.copy(), 'error')
    num_defects_text = index + 1
    draw_img_1 = image_1.copy()
    draw_img_2 = image_2.copy()

    h1, w1 = draw_img_1.shape[:2]
    h2, w2 = draw_img_2.shape[:2]

    size = 1000 // 2
    size_2 = 200 // 2

    crop_w = size * 2
    crop_h = size * 2

    def safe_crop(img, x, y, img_w, img_h):
        """Return a black canvas with valid cropped region from img."""
        top = y - size
        left = x - size
        bottom = y + size
        right = x + size

        # Create black canvas
        canvas = np.zeros((crop_h, crop_w, 3), dtype=np.uint8)

        # Determine valid source area
        src_top = max(top, 0)
        src_left = max(left, 0)
        src_bottom = min(bottom, img_h)
        src_right = min(right, img_w)

        # Determine destination positions in canvas
        dst_top = src_top - top
        dst_left = src_left - left
        dst_bottom = dst_top + (src_bottom - src_top)
        dst_right = dst_left + (src_right - src_left)

        # Copy valid region into canvas
        canvas[dst_top:dst_bottom, dst_left:dst_right] = img[src_top:src_bottom, src_left:src_right]

        return canvas

    try:
        if data is not None:
            x = int(data[0])
            y = int(data[1])
            top_left = (x - size, y - size)
            bottom_right = (x + size, y + size)
            top_left_2 = (x - size_2, y - size_2)
            bottom_right_2 = (x + size_2, y + size_2)

            global rec_size
            if draw_p1:
                rec_size = cv2.rectangle(draw_img_1.copy(), top_left, bottom_right, (0, 0, 255), 5)
                rec_size_2 = cv2.rectangle(rec_size.copy(), top_left_2, bottom_right_2, (0, 0, 255), 5)
                draw_img_1 = safe_crop(rec_size_2, x, y, w1, h1)

            if draw_p2:
                rec_size = cv2.rectangle(draw_img_2.copy(), top_left, bottom_right, (0, 0, 255), 5)
                rec_size_2 = cv2.rectangle(rec_size.copy(), top_left_2, bottom_right_2, (0, 0, 255), 5)
                draw_img_2 = safe_crop(rec_size_2, x, y, w2, h2)

        ng_1_resize = cv2.resize(draw_img_1, (WIDTH, HEIGHT)) if draw_img_1.size > 0 else error_screen
        ng_2_resize = cv2.resize(draw_img_2, (WIDTH, HEIGHT)) if draw_img_2.size > 0 else error_screen

    except cv2.error as e:
        print(f'cv2 error: {e}')
        ng_1_resize = ng_2_resize = error_screen

    if data is not None:
        label_draw_1 = screen_display(ng_1_resize, 'ROUND', num_defects_text, num_defects_1) if draw_p1 else ng_1_resize
        label_draw_2 = screen_display(ng_2_resize, 'ROUND', num_defects_text, num_defects_2) if draw_p2 else ng_2_resize
        combined = np.hstack((label_draw_1, label_draw_2))
    else:
        combined = np.hstack((ng_1_resize, ng_2_resize))

    cv2.imshow("ezyroboNG", combined)
    cv2.waitKey(1)
    
def save_ng_img(is_ok, filename, ng_image, folder_name, rnd_offset=0):
    if os.path.ismount(MOUNT_NAME):
        sub_folder = FOLDER_OK if is_ok else FOLDER_NG
        origin_folder = os.path.join(MOUNT_NAME, folder_name, sub_folder, "1")
        ng_folder = os.path.join(MOUNT_NAME, folder_name, sub_folder, "2")

        os.makedirs(origin_folder, exist_ok=True)
        os.makedirs(ng_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"img{rnd + rnd_offset}_{sub_folder}_{timestamp}.jpg"

        if filename is not None:
            cv2.imwrite(os.path.join(origin_folder, new_filename), filename)

        if ng_image is not None:
            cv2.imwrite(os.path.join(ng_folder, new_filename), ng_image)
    
threading.Thread(target=recv_mvp, daemon=True).start()
threading.Thread(target=recv_mvp_2, daemon=True).start()
threading.Thread(target=check_key, daemon=True).start()
threading.Thread(target=check_state, daemon=True).start()
threading.Thread(target=camera_thd, daemon=True).start()

check_mount()
print("PI1 Ready ....... to START !")
try:
    while True:
        if state != PROCESS:
            time.sleep(0.1)
            continue
        
        try:
            xyz = robo_q.get(timeout=1)
        except queue.Empty:
            continue

        E.move(xyz)
        send_pi2('start')
        print(f'ROUND {rnd + 1} at', xyz)
        cam_q.put(rnd)
        
        while True:
            if state == EMERGENCY:
                break
        
            try:
                mvp = mvp_res_q.get(timeout=0.1)
                if mvp:
                    print('MVP response:',mvp)
                break
            except queue.Empty:
                continue
            
        if state == EMERGENCY:
            continue

        # Load image or ok_screen.
        if state != EMERGENCY:
            time.sleep(0.1)
            filename_1 = os.path.join(MOUNT_NAME, FOLDER_NAME_1, "img.jpg")
            filename_2 = os.path.join(MOUNT_NAME, FOLDER_NAME_2, "img.jpg")

            if filename_1 and os.path.exists(filename_1):
                ori_image_1 = cv2.imread(filename_1)
                
            if filename_2 and os.path.exists(filename_2):
                ori_image_2 = cv2.imread(filename_2)
                
            ok_screen = screen_display(green_screen.copy(), 'OK')
            ng_screen = screen_display(red_screen.copy(), 'NG')
            
            image_1 = ori_image_1 if len(new_data_1) > 1 else ok_screen
            image_2 = ori_image_2 if len(new_data_2) > 1 else ok_screen
            
        if state == EMERGENCY:
            continue
                
        if mvp and (len(new_data_1) > 1 or len(new_data_2) >1):
            num_defects_1 = (len(new_data_1) - 1) // 2
            num_defects_2 = (len(new_data_2) - 1) // 2
            defects_idx_1 = 0
            defects_idx_2 = 0
            print("PI1 have", num_defects_1, "defects")
            print("PI2 have", num_defects_2, "defects")
            
            if len(new_data_1) > 1:
                for defects_idx_1 in range(num_defects_1):
                    if state == EMERGENCY:
                        break
                    del_str = new_data_1[1:]
                    xy_detect = del_str[2*defects_idx_1 : 2*defects_idx_1 + 2]
                    if len(new_data_2) > 1 :
                        image_2 = screen_display(yellow_screen,'Waiting for inspection')
                    ng_image_display(image_1, image_2, defects_idx_1, xy_detect, draw_p1=True, draw_p2=False)
                    while True:
                        if state == EMERGENCY:
                            break
                        if ch_pressed == 'c'or bt_confirm_ok.is_held:
                            while bt_confirm_ok.is_held:
                                time.sleep(0.05)
                            image_1 = ok_screen.copy()
                            save_ng_img(True, ori_image_1, rec_size, FOLDER_NAME_1)
                            ng_image_display(image_1, image_2, defects_idx_1)
                            time.sleep(0.3)
                            ch_pressed = None     
                            if defects_idx_1 != num_defects_1-1:
                                image_1 = ori_image_1
                            break
                        elif ch_pressed == 'z' or bt_confirm_ng.is_held:
                            while bt_confirm_ng.is_held:
                                time.sleep(0.05)
                            image_1 = ng_screen.copy()
                            save_ng_img(False, ori_image_1, rec_size, FOLDER_NAME_1)
                            ng_image_display(image_1, image_2, defects_idx_1)
                            time.sleep(0.3)
                            confirm_ng = True
                            ch_pressed = None     
                            break
                    if confirm_ng:
                        break
                    
            if len(new_data_2) > 1 and not confirm_ng:
                for defects_idx_2 in range(num_defects_2):
                    if state == EMERGENCY:
                        break
                    del_str = new_data_2[1:]
                    xy_detect = del_str[2*defects_idx_2 : 2*defects_idx_2 + 2]
                    image_2 = ori_image_2
                    ng_image_display(image_1, image_2, defects_idx_2, xy_detect, draw_p1=False, draw_p2=True)
                    while True:
                        if state == EMERGENCY:
                            break
                        if ch_pressed == 'c' or bt_confirm_ok.is_held:
                            while bt_confirm_ok.is_held:
                                time.sleep(0.05)
                            image_2 = ok_screen.copy()
                            save_ng_img(True, ori_image_2, rec_size, FOLDER_NAME_2,3)
                            ng_image_display(image_1, image_2, defects_idx_2)
                            time.sleep(0.3)
                            ch_pressed = None 
                            break
                        elif ch_pressed == 'z' or bt_confirm_ng.is_held:
                            while bt_confirm_ng.is_held:
                                time.sleep(0.05)
                            image_2 = ng_screen.copy()
                            save_ng_img(False, ori_image_2, rec_size, FOLDER_NAME_2,3)
                            ng_image_display(image_1, image_2, defects_idx_2)
                            time.sleep(0.3)
                            ch_pressed = None  
                            confirm_ng = True
                            break
                    if confirm_ng:
                        break
                    
            if ((defects_idx_1 == num_defects_1 - 1 or num_defects_1 == 0) and 
                (defects_idx_2 == num_defects_2 - 1 or num_defects_2 == 0)) or confirm_ng:
                cv2.destroyWindow('ezyroboNG')

        new_data.clear()
        rnd += 1

        if state == EMERGENCY:
            continue

        if rnd >= len(steps) or confirm_ng:
            state = FINISH

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    E.move(origin_step)
    E.toOrigin()
    E.send_close()
    print("EXIT program.")
                
            
        
        
