import cv2
import pyautogui
import time

# Load Haar cascades
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')

cap = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()

# Blink logic variables
blink_start_time = None
last_blink_time = 0
blink_duration_threshold = 0.6  # seconds → Long blink for left click
double_blink_max_gap = 1.2      # seconds → Two short blinks = right click
blink_ready = True

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    face_detected = False
    eyes_detected = False

    for (x, y, w, h) in faces:
        face_detected = True
        face_roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(face_roi_gray)

        if len(eyes) >= 2:
            eyes_detected = True
            eye_positions = [(ex + ew//2 + x, ey + eh//2 + y) for (ex, ey, ew, eh) in eyes[:2]]
            avg_eye_x = sum(p[0] for p in eye_positions) // 2
            avg_eye_y = sum(p[1] for p in eye_positions) // 2

            screen_x = int((avg_eye_x / frame.shape[1]) * screen_w)
            screen_y = int((avg_eye_y / frame.shape[0]) * screen_h)
            pyautogui.moveTo(screen_x, screen_y, duration=0.1)

            for (ex, ey) in eye_positions:
                cv2.circle(frame, (ex, ey), 10, (0, 255, 0), 2)

        break

    current_time = time.time()

    # Long blink OR double blink detection
    if face_detected and not eyes_detected:
        if blink_start_time is None:
            blink_start_time = current_time
    else:
        if blink_start_time is not None:
            blink_duration = current_time - blink_start_time

            if blink_duration >= blink_duration_threshold:
                # Long blink → left click
                pyautogui.click()
                print("Left click (long blink)")
                last_blink_time = 0  # reset double blink chain
            else:
                # Short blink → check for double blink
                if blink_ready and current_time - last_blink_time < double_blink_max_gap:
                    pyautogui.click(button='right')
                    print("Right click (double blink)")
                    blink_ready = False  # avoid triple click
                else:
                    last_blink_time = current_time
                    blink_ready = True

            blink_start_time = None  # reset

    cv2.imshow("Eye Mouse Control", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
