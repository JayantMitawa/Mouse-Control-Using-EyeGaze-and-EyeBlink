import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import time
from PIL import ImageGrab
from math import dist

# Initialize Mediapipe
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Screen dimensions
screen_w, screen_h = pyautogui.size()

# Eye landmark indices
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Smile and scroll thresholds
SMILE_THRESH = 0.05
SCROLL_THRESH = 0.03
SMOOTHING_FACTOR = 0.7

# Blink detection thresholds
EAR_THRESHOLD = 0.22
BLINK_DURATION = 0.15
DOUBLE_BLINK_INTERVAL = 0.5
last_left_blink_time = 0
last_right_blink_time = 0
last_both_blink_time = 0

# Variables
smoothed_x, smoothed_y = screen_w // 2, screen_h // 2
action_log = []

# EAR calculation
def calculate_EAR(eye_points, landmarks, image_shape):
    h, w = image_shape
    coords = [np.array([landmarks[p].x * w, landmarks[p].y * h]) for p in eye_points]
    vertical = (dist(coords[1], coords[5]) + dist(coords[2], coords[4])) / 2.0
    horizontal = dist(coords[0], coords[3])
    return vertical / horizontal

# Blink detection with left, right, double click
def detect_blink(left_ear, right_ear):
    global last_left_blink_time, last_right_blink_time, last_both_blink_time
    current_time = time.time()
    blinked_left = left_ear < EAR_THRESHOLD
    blinked_right = right_ear < EAR_THRESHOLD

    if blinked_left and blinked_right:
        if current_time - last_both_blink_time > DOUBLE_BLINK_INTERVAL:
            action_log.append("Double Blink - Double Click")
            pyautogui.doubleClick()
            last_both_blink_time = current_time
        return

    if blinked_left and not blinked_right:
        if current_time - last_left_blink_time > BLINK_DURATION:
            action_log.append("Left Eye Blink - Left Click")
            pyautogui.click()
            last_left_blink_time = current_time

    elif blinked_right and not blinked_left:
        if current_time - last_right_blink_time > BLINK_DURATION:
            action_log.append("Right Eye Blink - Right Click")
            pyautogui.rightClick()
            last_right_blink_time = current_time

# Finger counting
def count_fingers(hand_landmarks):
    tip_ids = [4, 8, 12, 16, 20]
    fingers = []

    # Thumb
    if hand_landmarks.landmark[tip_ids[0]].x < hand_landmarks.landmark[tip_ids[0]-1].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Other fingers
    for id in range(1, 5):
        if hand_landmarks.landmark[tip_ids[id]].y < hand_landmarks.landmark[tip_ids[id]-2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    return sum(fingers)

# Start webcam
cap = cv2.VideoCapture(0)

print("Gesture-based mouse control started. Press 'q' to exit.")

while True:
    success, frame = cap.read()
    if not success:
        continue

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = frame.shape[:2]

    face_results = face_mesh.process(rgb_frame)
    hand_results = hands.process(rgb_frame)

    if face_results.multi_face_landmarks:
        landmarks = face_results.multi_face_landmarks[0].landmark

        # Nose for mouse control
        nose = landmarks[4]
        mouse_x = int(nose.x * screen_w)
        mouse_y = int(nose.y * screen_h)
        smoothed_x = SMOOTHING_FACTOR * smoothed_x + (1 - SMOOTHING_FACTOR) * mouse_x
        smoothed_y = SMOOTHING_FACTOR * smoothed_y + (1 - SMOOTHING_FACTOR) * mouse_y
        pyautogui.moveTo(smoothed_x, smoothed_y)

        # Blink Detection
        left_ear = calculate_EAR(LEFT_EYE, landmarks, frame.shape[:2])
        right_ear = calculate_EAR(RIGHT_EYE, landmarks, frame.shape[:2])
        detect_blink(left_ear, right_ear)

        # Head tilt for scrolling
        head_tilt = landmarks[10].y - landmarks[152].y
        if abs(head_tilt) > SCROLL_THRESH:
            scroll_amount = int(head_tilt * 1000)
            pyautogui.scroll(scroll_amount)
            action_log.append(f"Scroll: {scroll_amount}")

        # Smile for tab switch
        mouth_width = abs(landmarks[61].x - landmarks[291].x)
        if mouth_width > SMILE_THRESH:
            action_log.append("Smile - Switch Tab")
            pyautogui.hotkey('ctrl', 'tab')

    # Hand gesture detection
    if hand_results.multi_hand_landmarks:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            fingers = count_fingers(hand_landmarks)

            if fingers == 0:  # ✊
                action_log.append("Show Keyboard (✊)")
                pyautogui.hotkey('win', 'ctrl', 'o')  # Example: on-screen keyboard
            elif fingers == 2:  # ✌
                action_log.append("Copy (✌)")
                pyautogui.hotkey('ctrl', 'c')
            elif fingers == 1:  # 👍
                action_log.append("Paste (👍)")
                pyautogui.hotkey('ctrl', 'v')
            elif fingers == 3:  # 🤟
                action_log.append("Undo (🤟)")
                pyautogui.hotkey('ctrl', 'z')
            elif fingers == 5:  # Full hand
                action_log.append("Screen Capture (Full hand)")
                ImageGrab.grab().save("screenshot.png")

    # Show latest actions
    cv2.putText(frame, "Actions: " + ", ".join(action_log[-3:]), (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Gesture Mouse Control", frame)
    action_log = action_log[-10:]  # Trim log

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()