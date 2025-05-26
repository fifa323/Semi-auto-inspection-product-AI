import cv2
import os
import numpy as np

WIDTH_4K = 3840
HEIGHT_4K = 2160
WIDTH = 640
HEIGHT = 480

CAMERA_INDEX = 0
        
origin_step = [0,0,0]

def set_camera_control(control, value):
    command = f"v4l2-ctl -d /dev/video0 --set-ctrl={control}={value}"
    os.system(command)
    
def update_brightness(val):
    set_camera_control("brightness", val)

def update_contrast(val):
    set_camera_control("contrast", val)

def update_saturation(val):
    set_camera_control("saturation", val)
    
def camera_thd():
    global frame, cap
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH_4K)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT_4K)
    #cap.set(cv2.CAP_PROP_EXPOSURE,13000)
    # cap.set(CAP_PROP_AUTO_WB,1)
    print(cap.get(cv2.CAP_PROP_EXPOSURE))
    print(cap.get(cv2.CAP_PROP_AUTO_WB))
    
    b = int(cap.get(cv2.CAP_PROP_BRIGHTNESS))
    c = int(cap.get(cv2.CAP_PROP_CONTRAST))
    s = int(cap.get(cv2.CAP_PROP_SATURATION))

    cv2.namedWindow("Camera1")
    cv2.namedWindow("Camera Settings")
    cv2.createTrackbar("Brightness", "Camera Settings", b, 100, update_brightness)
    cv2.createTrackbar("Contrast", "Camera Settings", c, 100, update_contrast)
    cv2.createTrackbar("Saturation", "Camera Settings", s, 100, update_saturation)
    
    cv2.setMouseCallback("Camera1", on_mouse_click)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = cv2.resize(frame, (WIDTH, HEIGHT))
        
        fx = frame.shape[1] / WIDTH 
        fy = frame.shape[0] / HEIGHT 

        x_orig = int(clicked_pos[0] * fx)
        y_orig = int(clicked_pos[1] * fy)

        x_orig = min(frame.shape[1] - 1, x_orig)
        y_orig = min(frame.shape[0] - 1, y_orig)

        b, g, r = frame[y_orig, x_orig]
        clicked_rgb = (r, g, b)
        
        # Draw on frame
        cv2.circle(resized_frame, clicked_pos, 5, (0, 255, 0), -1)
        cv2.putText(resized_frame, f"Pos: {clicked_pos}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(resized_frame, f"RGB: {clicked_rgb}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Camera1", resized_frame)

        settings_display = 255 * np.ones((150, 300, 3), dtype=np.uint8)
        cv2.putText(settings_display, f"Pos: {clicked_pos}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(settings_display, f"RGB: {clicked_rgb}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.imshow("Camera Settings", settings_display)

        key = cv2.waitKey(1)
        if key == 27: 
            break

    cap.release()
   
clicked_pos = (0, 0) 
clicked_rgb = (0, 0, 0)  

def on_mouse_click(event, x, y, flags, param):
    global clicked_pos, clicked_rgb, frame
    if event == cv2.EVENT_LBUTTONDOWN:
        if frame is not None:
            clicked_pos = (x, y)

cv2.startWindowThread()
print("Ready ....... to START !")
try:
    while True:
        camera_thd()
except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    print("EXIT program.")


