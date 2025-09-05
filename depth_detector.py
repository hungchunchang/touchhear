# ******************************************************************************
#  Copyright (c) 2024 Orbbec 3D Technology, Inc
#  
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.  
#  You may obtain a copy of the License at
#  
#      http://www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************

import cv2
import numpy as np
import mediapipe as mp
from flask import Response
import time

from pyorbbecsdk import *
from utils import frame_to_bgr_image

class A4DepthStreamDetector:
    def __init__(self):
        # MediaPipe 手部檢測 - 專注於食指
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # ArUco 檢測器
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        # Orbbec 深度相機設定 - 簡化初始化
        self.pipeline = Pipeline()
        self.pipeline.start()
        print("✓ Orbbec pipeline started successfully.")
        
        # 深度參數
        self.MIN_DEPTH = 20    # 20mm
        self.MAX_DEPTH = 2000  # 2000mm (2公尺)
        self.TOUCH_DEPTH_THRESHOLD = 30  # 30mm 接觸閾值 (更敏感)
        self.HOVER_DEPTH_THRESHOLD = 80  # 80mm 懸停閾值
        
        self.detection_results = {"board": False, "hands": [], "detected_markers": []}
        
        # A4 參考尺寸 (210mm x 297mm)
        self.a4_width = 210
        self.a4_height = 297
        
        # 平面深度參考
        self.paper_depth_reference = None
        self.calibration_frames = 0
        self.max_calibration_frames = 30
        
    def __del__(self):
        """清理資源"""
        try:
            if hasattr(self, 'pipeline'):
                self.pipeline.stop()
                print("✓ Pipeline stopped.")
        except:
            pass
            
    def get_frames(self):
        """獲取彩色和深度幀"""
        try:
            frames = self.pipeline.wait_for_frames(100)
            if frames is None:
                return None, None, None
                
            # 獲取彩色幀
            color_frame = frames.get_color_frame()
            if color_frame is None:
                return None, None, None
            color_image = frame_to_bgr_image(color_frame)
            
            # 獲取深度幀
            depth_frame = frames.get_depth_frame()
            if depth_frame is None:
                return None, None, None
                
            if depth_frame.get_format() != OBFormat.Y16:
                return None, None, None
                
            # 處理深度數據
            width = depth_frame.get_width()
            height = depth_frame.get_height()
            scale = depth_frame.get_depth_scale()
            
            depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16).reshape((height, width))
            depth_data = depth_data.astype(np.float32) * scale
            
            # 過濾無效深度值
            depth_data = np.where((depth_data > self.MIN_DEPTH) & (depth_data < self.MAX_DEPTH), 
                                 depth_data, 0)
            
            return color_image, depth_data, scale
            
        except Exception as e:
            print(f"Error getting frames: {e}")
            return None, None, None
    
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
        """檢測手部 - 優先處理食指"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_image)
        
        hand_landmarks = []
        
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmark in enumerate(results.multi_hand_landmarks):
                self.mp_drawing.draw_landmarks(
                    image, hand_landmark, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(255,255,255), thickness=2))
                
                h, w, _ = image.shape
                
                # 主要追蹤食指 (landmark 8)
                finger_tip = hand_landmark.landmark[8]
                finger_pos = (int(finger_tip.x * w), int(finger_tip.y * h))
                hand_landmarks.append(finger_pos)
                
                # 特別標記食指
                cv2.circle(image, finger_pos, 10, (0, 255, 0), -1)
                cv2.putText(image, f'Index {hand_idx+1}', 
                           (finger_pos[0] + 15, finger_pos[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return hand_landmarks, image
    
    def calibrate_paper_depth(self, depth_data, marker_positions):
        """校準紙張深度基準"""
        if not marker_positions or len(marker_positions) < 3:
            return
            
        # 獲取標記區域的深度值
        depth_values = []
        for pos in marker_positions.values():
            x, y = pos
            if 0 <= x < depth_data.shape[1] and 0 <= y < depth_data.shape[0]:
                # 取周圍區域的平均深度
                roi_size = 20
                x1, y1 = max(0, x-roi_size), max(0, y-roi_size)
                x2, y2 = min(depth_data.shape[1], x+roi_size), min(depth_data.shape[0], y+roi_size)
                
                roi_depth = depth_data[y1:y2, x1:x2]
                valid_depths = roi_depth[roi_depth > 0]
                
                if len(valid_depths) > 0:
                    depth_values.append(np.median(valid_depths))
        
        if len(depth_values) >= 2:
            current_paper_depth = np.median(depth_values)
            
            if self.paper_depth_reference is None:
                self.paper_depth_reference = current_paper_depth
            else:
                # 使用移動平均更新基準深度
                alpha = 0.1
                self.paper_depth_reference = (alpha * current_paper_depth + 
                                            (1 - alpha) * self.paper_depth_reference)
            
            self.calibration_frames = min(self.calibration_frames + 1, self.max_calibration_frames)
    
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
    
    def detect_finger_touch_depth(self, depth_data, finger_pos, paper_mask):
        """使用深度資訊檢測手指接觸狀態"""
        if paper_mask is None or self.paper_depth_reference is None:
            return "unknown", 0
            
        x, y = finger_pos
        if not (0 <= x < depth_data.shape[1] and 0 <= y < depth_data.shape[0]):
            return "unknown", 0
            
        # 檢查是否在紙張區域內
        if paper_mask[y, x] == 0:
            return "outside", 0
            
        # 獲取手指位置的深度
        radius = 15
        x1, y1 = max(0, x - radius), max(0, y - radius)
        x2, y2 = min(depth_data.shape[1], x + radius), min(depth_data.shape[0], y + radius)
        
        finger_depth_roi = depth_data[y1:y2, x1:x2]
        mask_roi = paper_mask[y1:y2, x1:x2]
        
        # 只考慮紙張區域內的深度值
        valid_depths = finger_depth_roi[(finger_depth_roi > 0) & (mask_roi > 0)]
        
        if len(valid_depths) < 5:
            return "nodata", 0
            
        finger_depth = np.median(valid_depths)
        depth_difference = self.paper_depth_reference - finger_depth
        
        # 判斷接觸狀態
        if depth_difference < self.TOUCH_DEPTH_THRESHOLD:
            contact_state = "touch"
        elif depth_difference < self.HOVER_DEPTH_THRESHOLD:
            contact_state = "hover"
        else:
            contact_state = "far"
        
        return contact_state, depth_difference
    
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
            
            try:
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
            except Exception as e:
                print(f"座標轉換錯誤: {e}")
        
        return None
    
    def draw_status_info(self, image, board_detected, detected_markers, touching_fingers, paper_depth_ref):
        """繪製狀態資訊"""
        # 基本狀態
        status_text = f"A4 棋盤: {'✓' if board_detected else '✗'} ({len(detected_markers)}/4 標記)"
        cv2.putText(image, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if board_detected else (0, 0, 255), 2)
        
        # 深度校準狀態 - 修正屬性名稱
        calibration_text = f"深度校準: {self.calibration_frames}/{self.max_calibration_frames}"
        if self.paper_depth_reference is not None:
            calibration_text += f" | 平面深度: {self.paper_depth_reference:.0f}mm"
        cv2.putText(image, calibration_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # 接觸狀態統計
        touch_count = len([f for f in touching_fingers if f.get('contact_state') == 'touch'])
        hover_count = len([f for f in touching_fingers if f.get('contact_state') == 'hover'])
        far_count = len([f for f in touching_fingers if f.get('contact_state') == 'far'])
        
        touch_text = f"Touch:{touch_count} Hover:{hover_count} Far:{far_count}"
        cv2.putText(image, touch_text, (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if touch_count > 0 else (255, 165, 0), 2)
        
        # 標記狀態
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
        
        # 顯示手指深度詳情
        if touching_fingers:
            for i, finger_data in enumerate(touching_fingers):
                if finger_data.get('a4_coord'):
                    coord_text = f"A4: ({finger_data['a4_coord'][0]}, {finger_data['a4_coord'][1]}) mm"
                    depth_diff = finger_data.get('depth_diff', 0)
                    state = finger_data.get('contact_state', 'unknown')
                    depth_text = f"距離: {depth_diff:.1f}mm - {state.upper()}"
                    
                    cv2.putText(image, coord_text, (10, 280 + i*40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    cv2.putText(image, depth_text, (10, 300 + i*40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    def detect_finger_touch_depth(self, depth_data, finger_pos, paper_mask):
        """使用深度資訊檢測手指接觸狀態"""
        if paper_mask is None or self.paper_depth_reference is None:
            return "unknown", 0, 0
            
        x, y = finger_pos
        if not (0 <= x < depth_data.shape[1] and 0 <= y < depth_data.shape[0]):
            return "unknown", 0, 0
            
        if paper_mask[y, x] == 0:
            return "outside", 0, 0
            
        # 獲取手指深度
        radius = 15
        x1, y1 = max(0, x - radius), max(0, y - radius)
        x2, y2 = min(depth_data.shape[1], x + radius), min(depth_data.shape[0], y + radius)
        
        finger_depth_roi = depth_data[y1:y2, x1:x2]
        mask_roi = paper_mask[y1:y2, x1:x2]
        
        valid_depths = finger_depth_roi[(finger_depth_roi > 0) & (mask_roi > 0)]
        
        if len(valid_depths) < 5:
            return "nodata", 0, 0
            
        finger_depth = np.median(valid_depths)
        depth_difference = self.paper_depth_reference - finger_depth
        
        # 判斷狀態
        if depth_difference < self.TOUCH_DEPTH_THRESHOLD:
            contact_state = "touch"
        elif depth_difference < self.HOVER_DEPTH_THRESHOLD:
            contact_state = "hover"
        else:
            contact_state = "far"
        
        return contact_state, depth_difference, finger_depth

    # 在 generate_frames 中的深度檢測部分修正：
    def generate_frames(self):
        """生成視頻幀"""
        while True:
            color_image, depth_data, scale = self.get_frames()
            if color_image is None or depth_data is None:
                continue
                
            display_frame = color_image.copy()
            
            # ArUco 檢測
            board_detected, marker_positions, detected_markers, display_frame = self.detect_aruco_markers(display_frame)
            
            # 校準深度
            if board_detected:
                self.calibrate_paper_depth(depth_data, marker_positions)
            
            # 創建遮罩
            paper_mask = self.create_paper_mask(display_frame, marker_positions)
            
            # 手部檢測
            hand_positions, display_frame = self.detect_hands(display_frame)
            
            # 深度接觸檢測
            touching_fingers = []
            if board_detected and hand_positions and self.calibration_frames > 10:
                for i, finger_pos in enumerate(hand_positions):
                    contact_state, depth_diff, finger_depth = self.detect_finger_touch_depth(depth_data, finger_pos, paper_mask)
                    
                    # 視覺化
                    if contact_state == "touch":
                        color = (0, 0, 255)  # 紅色
                        radius = 15
                    elif contact_state == "hover":
                        color = (255, 165, 0)  # 橙色
                        radius = 12
                    else:
                        color = (255, 0, 0)  # 藍色
                        radius = 8
                        
                    cv2.circle(display_frame, finger_pos, radius, color, 2)
                    
                    # 顯示深度資訊
                    status_text = f"{contact_state.upper()}: {depth_diff:.1f}mm"
                    cv2.putText(display_frame, status_text, 
                               (finger_pos[0]-40, finger_pos[1]-25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    
                    # 顯示實際深度 - 這是關鍵
                    if finger_depth > 0:
                        depth_text = f"深度: {finger_depth:.0f}mm"
                        cv2.putText(display_frame, depth_text, 
                                   (finger_pos[0]-40, finger_pos[1]+15),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    
                    # 計算 A4 座標
                    a4_coord = self.pixel_to_a4_coordinate(finger_pos, marker_positions)
                    if a4_coord:
                        finger_data = {
                            "position": finger_pos, 
                            "a4_coord": a4_coord,
                            "depth_diff": depth_diff,
                            "finger_depth": finger_depth,
                            "contact_state": contact_state
                        }
                        touching_fingers.append(finger_data)
                        
                        # 主控台輸出 - 像範例一樣
                        print(f"手指: {finger_depth:.0f}mm | 平面: {self.paper_depth_reference:.0f}mm | "
                              f"距離: {abs(depth_diff):.0f}mm | {contact_state.upper()}")
            
            # 顯示狀態
            self.draw_status_info(display_frame, board_detected, detected_markers, 
                                 touching_fingers, self.paper_depth_reference)
            
            # 更新結果
            self.detection_results = {
                "board": board_detected,
                "hands": touching_fingers if touching_fingers else [{"position": pos, "a4_coord": None} for pos in hand_positions],
                "detected_markers": detected_markers,
                "depth_reference": float(self.paper_depth_reference) if self.paper_depth_reference is not None else None,
                "calibration_progress": self.calibration_frames / self.max_calibration_frames
            }
            
            # 編碼輸出
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    
    def get_video_stream(self):
        """獲取視頻流"""
        return Response(self.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_detection_results(self):
        """獲取檢測結果"""
        results = {
            "board": bool(self.detection_results.get("board", False)),
            "hands": [],
            "detected_markers": [int(x) for x in self.detection_results.get("detected_markers", [])],
            "depth_reference": self.detection_results.get("depth_reference"),
            "calibration_progress": float(self.detection_results.get("calibration_progress", 0))
        }
        
        # 處理hands資料
        for hand in self.detection_results.get("hands", []):
            if isinstance(hand, dict):
                hand_data = {
                    "position": [int(hand["position"][0]), int(hand["position"][1])] if "position" in hand else None,
                    "a4_coord": [float(hand["a4_coord"][0]), float(hand["a4_coord"][1])] if hand.get("a4_coord") else None,
                    "finger_depth": float(hand.get("finger_depth", 0)),
                    "depth_diff": float(hand.get("depth_diff", 0)),
                    "contact_state": hand.get("contact_state", "unknown"),
                    "is_touching": hand.get("contact_state") == "touch"
                }
            else:
                hand_data = {
                    "position": [int(hand[0]), int(hand[1])],
                    "a4_coord": None,
                    "finger_depth": 0,
                    "depth_diff": 0,
                    "contact_state": "unknown",
                    "is_touching": False
                }
            results["hands"].append(hand_data)
        
        return results