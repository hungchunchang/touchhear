#!/usr/bin/env python3
import cv2
import numpy as np
import mediapipe as mp
from pyorbbecsdk import *
from utils import frame_to_bgr_image

class SimplifiedPlaneCalibration:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        self.pipeline = Pipeline()
        self.pipeline.start()
        
        # 簡化校正
        self.plane_depth = None
        self.calibration_count = 0
        self.is_calibrated = False
        
    def map_rgb_to_depth(self, rgb_x, rgb_y, rgb_shape, depth_shape):
        rgb_h, rgb_w = rgb_shape
        depth_h, depth_w = depth_shape
        return int(rgb_x * depth_w / rgb_w), int(rgb_y * depth_h / rgb_h)
    
    def get_depth_at_point(self, depth_image, depth_x, depth_y):
        h, w = depth_image.shape
        if not (0 <= depth_x < w and 0 <= depth_y < h):
            return None
            
        radius = 5
        x1, y1 = max(0, depth_x - radius), max(0, depth_y - radius)
        x2, y2 = min(w, depth_x + radius), min(h, depth_y + radius)
        
        roi = depth_image[y1:y2, x1:x2]
        valid_depths = roi[roi > 0]
        
        if len(valid_depths) > 0:
            return np.median(valid_depths) / 1000.0  # 轉換為米
        return None
    
    def calibrate_simple_plane(self, marker_positions, depth_image, rgb_shape, depth_shape):
        """簡化平面校正 - 使用四點深度平均"""
        if len(marker_positions) < 3:
            return False
            
        depths = []
        for marker_id, rgb_pos in marker_positions.items():
            depth_x, depth_y = self.map_rgb_to_depth(rgb_pos[0], rgb_pos[1], rgb_shape, depth_shape)
            depth = self.get_depth_at_point(depth_image, depth_x, depth_y)
            if depth:
                depths.append(depth)
        
        if len(depths) >= 3:
            current_plane_depth = np.median(depths)
            
            if self.plane_depth is None:
                self.plane_depth = current_plane_depth
            else:
                # 移動平均更新
                alpha = 0.2
                self.plane_depth = alpha * current_plane_depth + (1 - alpha) * self.plane_depth
            
            self.calibration_count += 1
            if self.calibration_count >= 10:
                self.is_calibrated = True
            
            return True
        return False
    
    def detect_aruco_markers(self, image, depth_image, rgb_shape, depth_shape):
        corners, ids, _ = cv2.aruco.detectMarkers(image, self.aruco_dict, parameters=self.aruco_params)
        
        marker_positions = {}
        
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(image, corners, ids)
            
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in [0, 1, 2, 3]:
                    center = np.mean(corners[i][0], axis=0).astype(int)
                    marker_positions[marker_id] = tuple(center)
                    
                    # 顯示深度
                    depth_x, depth_y = self.map_rgb_to_depth(center[0], center[1], rgb_shape, depth_shape)
                    depth = self.get_depth_at_point(depth_image, depth_x, depth_y)
                    
                    if depth:
                        cv2.putText(image, f'ID{marker_id}: {depth*1000:.0f}mm', 
                                   (center[0]-30, center[1]-40),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 執行校正
        if marker_positions:
            self.calibrate_simple_plane(marker_positions, depth_image, rgb_shape, depth_shape)
        
        return marker_positions, image
    
    def run(self):
        print("簡化平面校正啟動")
        
        while True:
            frames = self.pipeline.wait_for_frames(100)
            if not frames:
                continue
                
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                continue
                
            color_image = frame_to_bgr_image(color_frame)
            rgb_h, rgb_w = color_image.shape[:2]
            
            depth_w = depth_frame.get_width()
            depth_h = depth_frame.get_height()
            depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
            depth_image = depth_data.reshape((depth_h, depth_w))
            
            # ArUco檢測與校正
            marker_positions, color_image = self.detect_aruco_markers(
                color_image, depth_image, (rgb_h, rgb_w), (depth_h, depth_w))
            
            # 顯示校正狀態
            if self.is_calibrated:
                status_color = (0, 255, 0)
                status_text = f"CALIBRATED - Plane: {self.plane_depth*1000:.1f}mm"
            else:
                status_color = (0, 255, 255)
                status_text = f"CALIBRATING... {self.calibration_count}/10"
            
            cv2.putText(color_image, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            # 手指檢測
            if self.is_calibrated:
                rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb)
                
                if results.multi_hand_landmarks:
                    for landmarks in results.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(color_image, landmarks, self.mp_hands.HAND_CONNECTIONS)
                        
                        finger_tip = landmarks.landmark[8]
                        rgb_x = int(finger_tip.x * rgb_w)
                        rgb_y = int(finger_tip.y * rgb_h)
                        
                        depth_x, depth_y = self.map_rgb_to_depth(rgb_x, rgb_y, (rgb_h, rgb_w), (depth_h, depth_w))
                        finger_depth = self.get_depth_at_point(depth_image, depth_x, depth_y)
                        
                        if finger_depth:
                            # 計算到平面距離
                            distance_to_plane = abs(finger_depth - self.plane_depth) * 1000  # mm
                            
                            # 接觸判斷
                            if distance_to_plane < 25:
                                color = (0, 0, 255)
                                status = "TOUCH"
                            elif distance_to_plane < 50:
                                color = (0, 165, 255)
                                status = "HOVER"
                            else:
                                color = (255, 0, 0)
                                status = "FAR"
                            
                            cv2.circle(color_image, (rgb_x, rgb_y), 12, color, -1)
                            cv2.putText(color_image, f'{status}: {distance_to_plane:.0f}mm', 
                                       (rgb_x + 15, rgb_y - 15),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            
                            print(f"手指: {finger_depth*1000:.0f}mm | 平面: {self.plane_depth*1000:.0f}mm | "
                                  f"距離: {distance_to_plane:.0f}mm | {status}")
            
            cv2.imshow('Simplified Plane Calibration', color_image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tracker = SimplifiedPlaneCalibration()
    tracker.run()