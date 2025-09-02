import cv2
import numpy as np
import mediapipe as mp
from flask import Flask, render_template, Response
import threading
import time

app = Flask(__name__)

class A4WebStreamDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # ArUco 檢測器
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        self.cap = cv2.VideoCapture(0)
        self.latest_frame = None
        self.detection_results = {"board": False, "hands": [], "detected_markers": []}
        
        # A4 參考尺寸 (210mm x 297mm，轉換為相對單位)
        self.a4_width = 210
        self.a4_height = 297
        
    def detect_aruco_markers(self, image):
        """檢測 ArUco 標記並返回詳細資訊"""
        corners, ids, _ = cv2.aruco.detectMarkers(image, self.aruco_dict, parameters=self.aruco_params)
        
        detected_markers = []
        marker_positions = {}
        
        if ids is not None:
            # 繪製檢測到的標記
            cv2.aruco.drawDetectedMarkers(image, corners, ids)
            
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in [0, 1, 2, 3]:  # 只關心四個角落標記
                    center = np.mean(corners[i][0], axis=0).astype(int)
                    marker_positions[marker_id] = tuple(center)
                    detected_markers.append(marker_id)
                    
                    # 標記檢測到的 ArUco ID
                    cv2.putText(image, f'ID:{marker_id}', 
                               (center[0]-20, center[1]-30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        board_detected = len(detected_markers) >= 3
        return board_detected, marker_positions, detected_markers, image
    
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
    
    def create_paper_mask(self, image, marker_positions):
        """根據ArUco標記創建紙張區域遮罩"""
        if not marker_positions or len(marker_positions) < 3:
            return None
            
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # 獲取標記點
        points = []
        for marker_id in sorted(marker_positions.keys()):
            points.append(marker_positions[marker_id])
        
        if len(points) >= 3:
            # 創建凸包作為紙張區域
            points_array = np.array(points, dtype=np.int32)
            hull = cv2.convexHull(points_array)
            cv2.fillPoly(mask, [hull], 255)
            
        return mask
    
    def detect_finger_shadow(self, image, finger_pos, paper_mask):
        """檢測手指周圍的陰影來判斷是否接觸紙面"""
        if paper_mask is None:
            return False
            
        # 在手指位置周圍創建感興趣區域
        radius = 30
        x, y = finger_pos
        roi_x1 = max(0, x - radius)
        roi_y1 = max(0, y - radius) 
        roi_x2 = min(image.shape[1], x + radius)
        roi_y2 = min(image.shape[0], y + radius)
        
        # 提取 ROI
        roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
        paper_roi = paper_mask[roi_y1:roi_y2, roi_x1:roi_x2]
        
        if roi.size == 0 or paper_roi.size == 0:
            return False
        
        # 轉換為灰階並應用紙張遮罩
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        masked_roi = cv2.bitwise_and(gray_roi, paper_roi)
        
        # 計算平均亮度
        paper_pixels = masked_roi[paper_roi > 0]
        if len(paper_pixels) < 10:
            return False
            
        avg_brightness = np.mean(paper_pixels)
        
        # 如果亮度低於閾值，認為有陰影（接觸）
        shadow_threshold = 180  # 可調整
        is_touching = avg_brightness < shadow_threshold
        
        # 可視化陰影檢測區域
        if is_touching:
            cv2.circle(image, (x, y), radius, (0, 0, 255), 2)  # 紅色：接觸
            cv2.putText(image, f'Touch: {avg_brightness:.1f}', 
                       (x-30, y-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        else:
            cv2.circle(image, (x, y), radius, (255, 0, 0), 1)  # 藍色：懸空
            cv2.putText(image, f'Hover: {avg_brightness:.1f}', 
                       (x-30, y-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        return is_touching
    
    def pixel_to_a4_coordinate(self, pixel_pos, marker_positions):
        """將像素座標轉換為 A4 紙座標系統"""
        if not marker_positions or len(marker_positions) < 3:
            return None
        
        # A4 紙上標記的理論位置 (以 mm 為單位)
        margin = 10
        marker_refs = {
            0: [margin, margin],                                    # 左上
            1: [self.a4_width - margin, margin],                   # 右上  
            2: [self.a4_width - margin, self.a4_height - margin],  # 右下
            3: [margin, self.a4_height - margin]                   # 左下
        }
        
        # 收集對應點
        src_points = []
        dst_points = []
        for marker_id, pos in marker_positions.items():
            if marker_id in marker_refs:
                src_points.append(pos)
                dst_points.append(marker_refs[marker_id])
        
        if len(src_points) >= 3:
            src_points = np.float32(src_points)
            dst_points = np.float32(dst_points)
            
            if len(src_points) == 3:
                matrix = cv2.getAffineTransform(src_points, dst_points)
                pixel_array = np.array([[pixel_pos[0]], [pixel_pos[1]], [1]], dtype=np.float32)
                a4_coord = np.dot(matrix, pixel_array).flatten()
                x, y = a4_coord[0], a4_coord[1]
            else:
                matrix = cv2.getPerspectiveTransform(src_points, dst_points)
                pixel_array = np.float32([[pixel_pos]])
                a4_coord = cv2.perspectiveTransform(pixel_array, matrix)
                x, y = a4_coord[0][0][0], a4_coord[0][0][1]
            
            if 0 <= x <= self.a4_width and 0 <= y <= self.a4_height:
                return (round(x, 1), round(y, 1))
        
        return None
    
    def draw_marker_status(self, image, detected_markers):
        """在畫面上顯示標記檢測狀態"""
        marker_names = {0: "左上", 1: "右上", 2: "右下", 3: "左下"}
        
        # 顯示標題
        cv2.putText(image, "ArUco 標記狀態:", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        for i, (marker_id, name) in enumerate(marker_names.items()):
            y_pos = 150 + i * 25
            color = (0, 255, 0) if marker_id in detected_markers else (0, 0, 255)
            status = "✓" if marker_id in detected_markers else "✗"
            
            text = f"ID{marker_id} ({name}): {status}"
            cv2.putText(image, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    def generate_frames(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            display_frame = frame.copy()
            
            # 檢測 ArUco 標記
            board_detected, marker_positions, detected_markers, display_frame = self.detect_aruco_markers(display_frame)
            
            # 創建紙張遮罩（用於陰影檢測）
            paper_mask = self.create_paper_mask(display_frame, marker_positions)
            
            # 檢測手部
            hand_positions, display_frame = self.detect_hands(display_frame)
            
            # 檢查手指是否接觸紙面
            touching_fingers = []
            if board_detected and hand_positions and paper_mask is not None:
                for finger_pos in hand_positions:
                    is_touching = self.detect_finger_shadow(display_frame, finger_pos, paper_mask)
                    if is_touching:
                        a4_coord = self.pixel_to_a4_coordinate(finger_pos, marker_positions)
                        if a4_coord:
                            touching_fingers.append({"position": finger_pos, "a4_coord": a4_coord})
            
            # 顯示主要狀態
            status_text = f"A4 棋盤: {'✓' if board_detected else '✗'} ({len(detected_markers)}/4 標記)"
            cv2.putText(display_frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if board_detected else (0, 0, 255), 2)
            
            hand_text = f"手部: {'✓' if hand_positions else '✗'}"
            cv2.putText(display_frame, hand_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hand_positions else (0, 0, 255), 2)
            
            touch_text = f"接觸: {'✓' if touching_fingers else '✗'} ({len(touching_fingers)})"
            cv2.putText(display_frame, touch_text, (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if touching_fingers else (0, 0, 255), 2)
            
            # 顯示標記檢測詳情
            self.draw_marker_status(display_frame, detected_markers)
            
            # 只有接觸紙面才顯示座標
            if touching_fingers:
                for i, finger_data in enumerate(touching_fingers):
                    coord_text = f"A4 位置: ({finger_data['a4_coord'][0]}, {finger_data['a4_coord'][1]}) mm"
                    cv2.putText(display_frame, coord_text, (10, 290 + i*20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                self.detection_results = {
                    "board": True,
                    "hands": touching_fingers,
                    "detected_markers": detected_markers
                }
            
            self.latest_frame = display_frame
            
            # 編碼為 JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

detector = A4WebStreamDetector()

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>A4 棋盤手勢檢測</title>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: Arial; 
                text-align: center; 
                background: #f0f0f0; 
                margin: 0;
                padding: 20px;
            }
            .container { 
                max-width: 900px; 
                margin: 0 auto; 
                padding: 20px; 
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            img { 
                border: 3px solid #333; 
                border-radius: 10px; 
                max-width: 100%;
                height: auto;
            }
            .status { 
                margin: 20px 0; 
                padding: 15px; 
                background: #f8f9fa; 
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }
            .instructions {
                text-align: left;
                background: #fff3cd;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
            }
            h1 { color: #333; margin-bottom: 10px; }
            .marker-info {
                background: #d1ecf1;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #17a2b8;
                margin: 10px 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 A4 棋盤手勢檢測系統</h1>
            <img src="/video_feed" width="640" height="480">
            
            <div class="instructions">
                <h3>📋 使用說明：</h3>
                <ol>
                    <li>列印 A4 模板（包含四個角落的 ArUco 標記）</li>
                    <li>將 A4 紙平放在攝影機前</li>
                    <li>用食指指向 A4 紙上的位置</li>
                    <li>系統會顯示手指在 A4 紙上的精確座標（單位：mm）</li>
                    <li>只有手指接觸紙面時才會記錄座標（陰影檢測）</li>
                </ol>
            </div>
            
            <div class="marker-info">
                <strong>ArUco 標記說明：</strong><br>
                • ID0 (左上角) • ID1 (右上角) • ID2 (右下角) • ID3 (左下角)<br>
                至少需要檢測到 3 個標記才能進行座標計算
            </div>
            
            <div class="status">
                <h3>💡 檢測狀態</h3>
                <p>即時影像中會顯示：</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>ArUco 標記檢測狀態（✓/✗）</li>
                    <li>手部檢測狀態</li>
                    <li>接觸檢測（紅圈=接觸，藍圈=懸空）</li>
                    <li>手指在 A4 紙上的精確位置 (mm)</li>
                </ul>
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
    print("啟動 A4 棋盤手勢檢測服務...")
    print("在瀏覽器開啟: http://localhost:5000")
    print("請確保已列印 A4 模板並放置在攝影機前")
    app.run(host='0.0.0.0', port=5000, debug=False)