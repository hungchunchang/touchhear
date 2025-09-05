#!/usr/bin/env python3
import cv2
import numpy as np
import mediapipe as mp
from pyorbbecsdk import *
from utils import frame_to_bgr_image

class CorrectDepthFingerTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.pipeline = Pipeline()
        self.pipeline.start()
        print("深度手指追蹤啟動")
        
    def map_rgb_to_depth(self, rgb_x, rgb_y, rgb_shape, depth_shape):
        """RGB座標映射到深度座標"""
        rgb_h, rgb_w = rgb_shape
        depth_h, depth_w = depth_shape
        
        depth_x = int(rgb_x * depth_w / rgb_w)
        depth_y = int(rgb_y * depth_h / rgb_h)
        
        return depth_x, depth_y
    
    def get_finger_depth(self, depth_image, depth_x, depth_y):
        """獲取手指深度 - 正確計算"""
        h, w = depth_image.shape
        
        if not (0 <= depth_x < w and 0 <= depth_y < h):
            return None
            
        # 周圍採樣
        radius = 8
        x1, y1 = max(0, depth_x - radius), max(0, depth_y - radius)
        x2, y2 = min(w, depth_x + radius), min(h, depth_y + radius)
        
        roi = depth_image[y1:y2, x1:x2]
        valid_depths = roi[roi > 0]
        
        if len(valid_depths) > 0:
            raw_depth = np.median(valid_depths)
            depth_meters = raw_depth / 1000.0  # 正確轉換
            return depth_meters
        return None
    
    def run(self):
        while True:
            frames = self.pipeline.wait_for_frames(100)
            if not frames:
                continue
                
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                continue
                
            # RGB影像
            color_image = frame_to_bgr_image(color_frame)
            rgb_h, rgb_w = color_image.shape[:2]
            
            # 深度數據
            depth_w = depth_frame.get_width()
            depth_h = depth_frame.get_height()
            depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
            depth_image = depth_data.reshape((depth_h, depth_w))
            
            # 手部檢測
            rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)
            
            if results.multi_hand_landmarks:
                for landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(color_image, landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # 食指指尖
                    finger_tip = landmarks.landmark[8]
                    rgb_x = int(finger_tip.x * rgb_w)
                    rgb_y = int(finger_tip.y * rgb_h)
                    
                    # 映射到深度座標
                    depth_x, depth_y = self.map_rgb_to_depth(rgb_x, rgb_y, (rgb_h, rgb_w), (depth_h, depth_w))
                    
                    # 獲取深度
                    depth_meters = self.get_finger_depth(depth_image, depth_x, depth_y)
                    
                    if depth_meters:
                        depth_mm = depth_meters * 1000
                        
                        # 視覺標記
                        cv2.circle(color_image, (rgb_x, rgb_y), 12, (0, 255, 0), -1)
                        cv2.putText(color_image, f'{depth_mm:.0f}mm', 
                                   (rgb_x + 15, rgb_y - 15),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        print(f"食指深度: {depth_mm:.1f}mm ({depth_meters:.3f}m)")
                    else:
                        cv2.circle(color_image, (rgb_x, rgb_y), 12, (0, 0, 255), 2)
                        cv2.putText(color_image, 'No Depth', (rgb_x + 15, rgb_y - 15),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # 顯示座標映射資訊
            cv2.putText(color_image, f"RGB: {rgb_w}x{rgb_h} -> Depth: {depth_w}x{depth_h}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow('Corrected Depth Finger Tracking', color_image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tracker = CorrectDepthFingerTracker()
    tracker.run()