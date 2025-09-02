import cv2
import numpy as np
import mediapipe as mp
from flask import Flask, render_template, Response
import threading
import time

app = Flask(__name__)

class WebStreamDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.chessboard_size = (7, 7)
        self.cap = cv2.VideoCapture(0)
        self.latest_frame = None
        self.detection_results = {"board": False, "hands": []}
        
    def detect_chessboard(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, self.chessboard_size, None)
        
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            cv2.drawChessboardCorners(image, self.chessboard_size, corners, ret)
            
        return ret, corners, image
    
    def detect_hands(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_image)
        
        hand_landmarks = []
        
        if results.multi_hand_landmarks:
            for hand_landmark in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    image, hand_landmark, self.mp_hands.HAND_CONNECTIONS)
                
                h, w, _ = image.shape
                finger_tip = hand_landmark.landmark[8]
                finger_pos = (int(finger_tip.x * w), int(finger_tip.y * h))
                hand_landmarks.append(finger_pos)
                
                cv2.circle(image, finger_pos, 10, (0, 255, 0), -1)
                cv2.putText(image, 'Finger', 
                           (finger_pos[0] + 15, finger_pos[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return hand_landmarks, image
    
    def pixel_to_board_coordinate(self, pixel_pos, corners):
        if corners is None or len(corners) < 49:
            return None
            
        top_left = corners[0][0]
        top_right = corners[6][0] 
        bottom_right = corners[48][0]
        bottom_left = corners[42][0]
        
        corner_points = np.float32([top_left, top_right, bottom_right, bottom_left])
        board_points = np.float32([[0, 0], [8, 0], [8, 8], [0, 8]])
        
        matrix = cv2.getPerspectiveTransform(corner_points, board_points * 100)
        pixel_array = np.float32([[pixel_pos]])
        board_coord = cv2.perspectiveTransform(pixel_array, matrix)
        
        x, y = board_coord[0][0]
        board_x, board_y = int(x // 100), int(y // 100)
        
        if 0 <= board_x < 8 and 0 <= board_y < 8:
            return (board_x, board_y)
        return None
    
    def generate_frames(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # 先在乾淨的幀檢測棋盤
            board_detected, corners, _ = self.detect_chessboard(frame.copy())

            # 再檢測手部（在原始幀上）
            hand_positions, display_frame = self.detect_hands(frame.copy())

            # 最後繪製棋盤到顯示幀
            if board_detected:
                cv2.drawChessboardCorners(display_frame, self.chessboard_size, corners, True)
            
            # 顯示狀態
            status_text = "棋盤: " + ("✓" if board_detected else "✗")
            cv2.putText(display_frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if board_detected else (0, 0, 255), 2)
            
            hand_text = f"手部: {'✓' if hand_positions else '✗'}"
            cv2.putText(display_frame, hand_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hand_positions else (0, 0, 255), 2)
            
            # 計算棋盤座標
            if board_detected and hand_positions:
                for finger_pos in hand_positions:
                    board_coord = self.pixel_to_board_coordinate(finger_pos, corners)
                    if board_coord:
                        coord_text = f"位置: {board_coord}"
                        cv2.putText(display_frame, coord_text, (10, 90), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                        self.detection_results = {
                            "board": True, 
                            "hands": [{"position": finger_pos, "board_coord": board_coord}]
                        }
            
            self.latest_frame = display_frame
            
            # 編碼為 JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

detector = WebStreamDetector()

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>棋盤手勢檢測</title>
        <style>
            body { font-family: Arial; text-align: center; background: #f0f0f0; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            img { border: 3px solid #333; border-radius: 10px; }
            .status { margin: 20px; padding: 10px; background: white; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 棋盤手勢檢測</h1>
            <img src="/video_feed" width="640" height="480">
            <div class="status">
                <p>將棋盤放在攝影機前，用食指指向棋盤位置</p>
                <p>程式會即時顯示檢測結果</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    return Response(detector.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("啟動 Web 串流服務...")
    print("在瀏覽器開啟: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)