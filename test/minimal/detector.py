# detector.py - 基礎檢測模組
import cv2
import numpy as np
import mediapipe as mp
from flask import Response

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
        self.detection_results = {"board": False, "hands": [], "detected_markers": []}
        
        # A4 參考尺寸 (210mm x 297mm)
        self.a4_width = 210
        self.a4_height = 297
        
    def detect_aruco_markers(self, image):
        """檢測 ArUco 標記"""
        corners, ids, _ = cv2.aruco.detectMarkers(image, self.aruco_dict, parameters=self.aruco_params)
        
        detected_markers = []
        marker_positions = {}
        
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(image, corners, ids)
            
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in [0, 1, 2, 3]:
                    center = np.mean(corners[i][0], axis=0).astype(int)
                    marker_positions[marker_id] = tuple(center)
                    detected_markers.append(marker_id)
                    
                    cv2.putText(image, f'ID:{marker_id}', 
                               (center[0]-20, center[1]-30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        board_detected = len(detected_markers) >= 3
        return board_detected, marker_positions, detected_markers, image
    
    def detect_hands(self, image):
        """檢測手部"""
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
        """創建紙張區域遮罩"""
        if not marker_positions or len(marker_positions) < 3:
            return None
            
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        points = []
        for marker_id in sorted(marker_positions.keys()):
            points.append(marker_positions[marker_id])
        
        if len(points) >= 3:
            points_array = np.array(points, dtype=np.int32)
            hull = cv2.convexHull(points_array)
            cv2.fillPoly(mask, [hull], 255)
            
        return mask
    
    def detect_finger_shadow(self, image, finger_pos, paper_mask):
        """檢測手指陰影判斷接觸"""
        if paper_mask is None:
            return False
            
        radius = 30
        x, y = finger_pos
        roi_x1 = max(0, x - radius)
        roi_y1 = max(0, y - radius) 
        roi_x2 = min(image.shape[1], x + radius)
        roi_y2 = min(image.shape[0], y + radius)
        
        roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
        paper_roi = paper_mask[roi_y1:roi_y2, roi_x1:roi_x2]
        
        if roi.size == 0 or paper_roi.size == 0:
            return False
        
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        masked_roi = cv2.bitwise_and(gray_roi, paper_roi)
        
        paper_pixels = masked_roi[paper_roi > 0]
        if len(paper_pixels) < 10:
            return False
            
        avg_brightness = np.mean(paper_pixels)
        shadow_threshold = 180
        is_touching = avg_brightness < shadow_threshold
        
        if is_touching:
            cv2.circle(image, (x, y), radius, (0, 0, 255), 2)
            cv2.putText(image, f'Touch: {avg_brightness:.1f}', 
                       (x-30, y-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        else:
            cv2.circle(image, (x, y), radius, (255, 0, 0), 1)
            cv2.putText(image, f'Hover: {avg_brightness:.1f}', 
                       (x-30, y-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        return is_touching
    
    def pixel_to_a4_coordinate(self, pixel_pos, marker_positions):
        """像素座標轉A4座標"""
        if not marker_positions or len(marker_positions) < 3:
            return None
        
        margin = 10
        marker_refs = {
            0: [margin, margin],
            1: [self.a4_width - margin, margin],
            2: [self.a4_width - margin, self.a4_height - margin],
            3: [margin, self.a4_height - margin]
        }
        
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
        """顯示標記狀態"""
        marker_names = {0: "左上", 1: "右上", 2: "右下", 3: "左下"}
        
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
        """生成視頻幀"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            display_frame = frame.copy()
            
            # 檢測標記和手部
            board_detected, marker_positions, detected_markers, display_frame = self.detect_aruco_markers(display_frame)
            paper_mask = self.create_paper_mask(display_frame, marker_positions)
            hand_positions, display_frame = self.detect_hands(display_frame)
            
            # 接觸檢測
            touching_fingers = []
            if board_detected and hand_positions and paper_mask is not None:
                for finger_pos in hand_positions:
                    is_touching = self.detect_finger_shadow(display_frame, finger_pos, paper_mask)
                    if is_touching:
                        a4_coord = self.pixel_to_a4_coordinate(finger_pos, marker_positions)
                        if a4_coord:
                            touching_fingers.append({"position": finger_pos, "a4_coord": a4_coord})
            
            # 顯示狀態
            status_text = f"A4 棋盤: {'✓' if board_detected else '✗'} ({len(detected_markers)}/4 標記)"
            cv2.putText(display_frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if board_detected else (0, 0, 255), 2)
            
            hand_text = f"手部: {'✓' if hand_positions else '✗'}"
            cv2.putText(display_frame, hand_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hand_positions else (0, 0, 255), 2)
            
            touch_text = f"接觸: {'✓' if touching_fingers else '✗'} ({len(touching_fingers)})"
            cv2.putText(display_frame, touch_text, (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if touching_fingers else (0, 0, 255), 2)
            
            self.draw_marker_status(display_frame, detected_markers)
            
            # 顯示座標
            if touching_fingers:
                for i, finger_data in enumerate(touching_fingers):
                    coord_text = f"A4 位置: ({finger_data['a4_coord'][0]}, {finger_data['a4_coord'][1]}) mm"
                    cv2.putText(display_frame, coord_text, (10, 290 + i*20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # 更新結果
            self.detection_results = {
                "board": board_detected,
                "hands": touching_fingers if touching_fingers else hand_positions,
                "detected_markers": detected_markers
            }
            
            # 編碼輸出
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    def get_video_stream(self):
        """獲取視頻流"""
        return Response(self.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_detection_results(self):
        """獲取檢測結果"""
        return self.detection_results