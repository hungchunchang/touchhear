#!/usr/bin/env python3
import cv2
import numpy as np
from pyorbbecsdk import *
from utils import frame_to_bgr_image

def debug_depth_values():
    pipeline = Pipeline()
    pipeline.start()
    
    print("調試深度值...")
    
    for i in range(5):
        frames = pipeline.wait_for_frames(100)
        if not frames:
            continue
            
        depth_frame = frames.get_depth_frame()
        if not depth_frame:
            continue
            
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        depth_scale = depth_frame.get_depth_scale()
        
        print(f"\n幀 {i+1}:")
        print(f"深度圖尺寸: {width}x{height}")
        print(f"深度比例: {depth_scale}")
        
        # 提取深度數據
        depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
        depth_image = depth_data.reshape((height, width))
        
        # 統計有效深度
        valid_depths = depth_image[depth_image > 0]
        print(f"有效深度像素: {len(valid_depths)}/{width*height}")
        
        if len(valid_depths) > 0:
            print(f"原始深度值範圍: {valid_depths.min()} - {valid_depths.max()}")
            print(f"深度距離範圍: {valid_depths.min()*depth_scale*1000:.1f} - {valid_depths.max()*depth_scale*1000:.1f} mm")
            
            # 測試不同轉換方法
            center_raw = depth_image[height//2, width//2]
            print(f"中心點原始值: {center_raw}")
            print(f"方法1 (×scale×1000): {center_raw * depth_scale * 1000:.1f} mm")
            print(f"方法2 (×scale): {center_raw * depth_scale:.3f} m")
            print(f"方法3 (直接/1000): {center_raw / 1000:.3f} m")
        else:
            print("無有效深度數據 - 檢查距離是否在0.25-5.5m範圍內")
    
    pipeline.stop()

def test_coordinate_mapping():
    """測試座標映射"""
    pipeline = Pipeline()
    pipeline.start()
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            color_image, depth_image, depth_scale = param
            
            # 將RGB座標映射到深度座標
            rgb_h, rgb_w = color_image.shape[:2]
            depth_h, depth_w = depth_image.shape
            
            # 簡單比例映射
            depth_x = int(x * depth_w / rgb_w)
            depth_y = int(y * depth_h / rgb_h)
            
            print(f"\nRGB點擊: ({x},{y}) 在 {rgb_w}x{rgb_h}")
            print(f"映射到深度: ({depth_x},{depth_y}) 在 {depth_w}x{depth_h}")
            
            if 0 <= depth_x < depth_w and 0 <= depth_y < depth_h:
                depth_raw = depth_image[depth_y, depth_x]
                if depth_raw > 0:
                    # 嘗試不同計算方法
                    method1 = depth_raw * depth_scale * 1000
                    method2 = depth_raw * depth_scale
                    method3 = depth_raw / 1000
                    
                    print(f"原始深度: {depth_raw}")
                    print(f"方法1: {method1:.1f}mm")
                    print(f"方法2: {method2:.3f}m")
                    print(f"方法3: {method3:.3f}m")
                else:
                    print("無深度數據")
    
    while True:
        frames = pipeline.wait_for_frames(100)
        if not frames:
            continue
            
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        
        if not color_frame or not depth_frame:
            continue
            
        color_image = frame_to_bgr_image(color_frame)
        
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        depth_scale = depth_frame.get_depth_scale()
        depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
        depth_image = depth_data.reshape((height, width))
        
        # 縮放深度圖到RGB尺寸
        depth_resized = cv2.resize(depth_image, (color_image.shape[1], color_image.shape[0]))
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_resized, alpha=0.1), cv2.COLORMAP_JET)
        
        # 疊加顯示
        overlay = cv2.addWeighted(color_image, 0.7, depth_colormap, 0.3, 0)
        
        cv2.putText(overlay, f"RGB: {color_image.shape[1]}x{color_image.shape[0]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(overlay, f"Depth: {width}x{height} (resized)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(overlay, "Click to test mapping", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        
        cv2.imshow('Coordinate Mapping Test', overlay)
        cv2.setMouseCallback('Coordinate Mapping Test', mouse_callback, (color_image, depth_image, depth_scale))
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    pipeline.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_depth_values()
    input("按Enter繼續座標映射測試...")
    test_coordinate_mapping()