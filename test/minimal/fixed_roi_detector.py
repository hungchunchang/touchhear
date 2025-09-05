#!/usr/bin/env python3
import sys
import json
import os
import cv2
import numpy as np
import mediapipe as mp
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pyorbbecsdk import *
from utils import frame_to_bgr_image
import pygame
import time

class FixedROIDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_detector()
        self.setup_audio()
        self.load_project()
        self.setup_timer()
        
    def setup_ui(self):
        self.setWindowTitle("TouchHear ROI Detector (Fixed)")
        self.setGeometry(100, 100, 1200, 800)
        
        layout = QHBoxLayout()
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid black")
        layout.addWidget(self.video_label, 2)
        
        # Status panel
        status_widget = self.create_status_panel()
        layout.addWidget(status_widget, 1)
        
        self.setLayout(layout)
        
    def create_status_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Detection Status")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Status items
        self.board_status = QLabel("ArUco Board: ✗")
        self.calibration_status = QLabel("Calibration: 0%")
        self.hand_status = QLabel("Hand: None")
        self.roi_status = QLabel("ROI Touches: 0")
        
        for label in [self.board_status, self.calibration_status, self.hand_status, self.roi_status]:
            label.setStyleSheet("padding: 5px; margin: 2px; background: #f0f0f0; border-radius: 3px;")
            layout.addWidget(label)
        
        # Progress bar
        layout.addWidget(QLabel("Calibration Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # ROI list
        layout.addWidget(QLabel("Project ROIs:"))
        self.roi_list = QListWidget()
        self.roi_list.setMaximumHeight(150)
        layout.addWidget(self.roi_list)
        
        # Touched ROIs
        layout.addWidget(QLabel("Currently Touched:"))
        self.touched_list = QListWidget()
        self.touched_list.setMaximumHeight(100)
        layout.addWidget(self.touched_list)
        
        # Audio controls
        layout.addWidget(QLabel("Audio Controls:"))
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        layout.addLayout(volume_layout)
        
        stop_btn = QPushButton("Stop All Audio")
        stop_btn.clicked.connect(self.stop_audio)
        layout.addWidget(stop_btn)
        
        # Load project button
        load_btn = QPushButton("Load Project")
        load_btn.clicked.connect(self.load_project_dialog)
        layout.addWidget(load_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def setup_detector(self):
        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)
        self.mp_drawing = mp.solutions.drawing_utils
        
        # ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        # Orbbec
        self.pipeline = Pipeline()
        self.pipeline.start()
        
        # Calibration
        self.plane_depth = None
        self.calibration_count = 0
        self.is_calibrated = False
        
        # Project data
        self.project_data = None
        self.editor_canvas_size = (800, 600)  # 編輯器畫布尺寸
        self.background_scale_info = None  # 背景縮放資訊
        
    def setup_audio(self):
        pygame.mixer.init()
        self.audio_cooldowns = {}
        self.volume = 0.7
        
    def load_project(self):
        project_file = "project_config.json"
        if os.path.exists(project_file):
            self.load_project_from_file(project_file)
                
    def load_project_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON (*.json)")
        if file_path:
            self.load_project_from_file(file_path)
            
    def load_project_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.project_data = json.load(f)
                
            self.calculate_background_scale()
            self.update_roi_list()
            
            roi_count = len(self.project_data.get('rois', []))
            QMessageBox.information(self, "Success", f"Loaded project with {roi_count} ROIs")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load project: {e}")
            
    def calculate_background_scale(self):
        """計算背景圖片在編輯器中的縮放資訊"""
        if not self.project_data or not self.project_data.get('background'):
            self.background_scale_info = None
            return
            
        bg_path = self.project_data['background']
        if not os.path.exists(bg_path):
            self.background_scale_info = None
            return
            
        # 載入背景圖片獲取原始尺寸
        bg_image = cv2.imread(bg_path)
        if bg_image is None:
            self.background_scale_info = None
            return
            
        bg_h, bg_w = bg_image.shape[:2]
        canvas_w, canvas_h = self.editor_canvas_size
        
        # 計算保持長寬比的縮放
        scale_w = canvas_w / bg_w
        scale_h = canvas_h / bg_h
        scale = min(scale_w, scale_h)
        
        # 計算縮放後的實際尺寸和位置
        scaled_w = int(bg_w * scale)
        scaled_h = int(bg_h * scale)
        offset_x = (canvas_w - scaled_w) // 2
        offset_y = (canvas_h - scaled_h) // 2
        
        self.background_scale_info = {
            'original_size': (bg_w, bg_h),
            'scaled_size': (scaled_w, scaled_h),
            'offset': (offset_x, offset_y),
            'scale': scale
        }
        
        print(f"Background scale info: {self.background_scale_info}")
                
    def update_roi_list(self):
        self.roi_list.clear()
        if not self.project_data:
            return
            
        for roi in self.project_data.get('rois', []):
            audio_status = "🔊" if roi.get('audio_file') and os.path.exists(roi.get('audio_file', '')) else "🔇"
            self.roi_list.addItem(f"{roi['name']} {audio_status}")
            
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 FPS
        
    def map_rgb_to_depth(self, rgb_x, rgb_y, rgb_shape, depth_shape):
        rgb_h, rgb_w = rgb_shape
        depth_h, depth_w = depth_shape
        return int(rgb_x * depth_w / rgb_w), int(rgb_y * depth_h / rgb_h)
    
    def get_depth_at_point(self, depth_image, depth_x, depth_y):
        h, w = depth_image.shape
        if not (0 <= depth_x < w and 0 <= depth_y < h):
            return None
        
        radius = 8
        x1, y1 = max(0, depth_x - radius), max(0, depth_y - radius)
        x2, y2 = min(w, depth_x + radius), min(h, depth_y + radius)
        
        roi = depth_image[y1:y2, x1:x2]
        valid_depths = roi[roi > 0]
        
        if len(valid_depths) > 0:
            return np.median(valid_depths) / 1000.0
        return None
    
    def calibrate_plane(self, marker_positions, depth_image, rgb_shape, depth_shape):
        if len(marker_positions) < 3:
            return False
        
        depths = []
        for rgb_pos in marker_positions.values():
            depth_x, depth_y = self.map_rgb_to_depth(rgb_pos[0], rgb_pos[1], rgb_shape, depth_shape)
            depth = self.get_depth_at_point(depth_image, depth_x, depth_y)
            if depth:
                depths.append(depth)
        
        if len(depths) >= 3:
            current_plane_depth = np.median(depths)
            
            if self.plane_depth is None:
                self.plane_depth = current_plane_depth
            else:
                alpha = 0.1
                self.plane_depth = alpha * current_plane_depth + (1 - alpha) * self.plane_depth
            
            self.calibration_count = min(self.calibration_count + 1, 30)
            if self.calibration_count >= 20:
                self.is_calibrated = True
            
            return True
        return False
    
    def pixel_to_a4_coordinate(self, pixel_pos, marker_positions):
        """將像素座標轉換為A4座標 (mm)"""
        if not marker_positions or len(marker_positions) < 3:
            return None
        
        # A4尺寸 (mm)
        a4_width_mm = 210
        a4_height_mm = 297
        margin_mm = 3
        
        marker_refs = {
            0: [margin_mm, margin_mm],
            1: [a4_width_mm - margin_mm, margin_mm],
            2: [a4_width_mm - margin_mm, a4_height_mm - margin_mm],
            3: [margin_mm, a4_height_mm - margin_mm]
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
                
                if 0 <= x <= a4_width_mm and 0 <= y <= a4_height_mm:
                    return (round(x, 1), round(y, 1))
            except Exception as e:
                print(f"Coordinate conversion error: {e}")
        
        return None
    
    def editor_roi_to_a4_mm(self, roi):
        """將編輯器ROI座標轉換為A4毫米座標"""
        if not self.background_scale_info:
            # 無背景圖片時，直接按編輯器畫布比例
            a4_x = roi['x'] * 210 / self.editor_canvas_size[0]
            a4_y = roi['y'] * 297 / self.editor_canvas_size[1]
            a4_w = roi['width'] * 210 / self.editor_canvas_size[0]
            a4_h = roi['height'] * 297 / self.editor_canvas_size[1]
        else:
            # 有背景圖片時，考慮背景縮放
            scale_info = self.background_scale_info
            
            # ROI相對於背景圖片的位置
            roi_x_in_bg = (roi['x'] - scale_info['offset'][0]) / scale_info['scale']
            roi_y_in_bg = (roi['y'] - scale_info['offset'][1]) / scale_info['scale']
            roi_w_in_bg = roi['width'] / scale_info['scale']
            roi_h_in_bg = roi['height'] / scale_info['scale']
            
            # 背景圖片映射到A4的比例
            bg_w, bg_h = scale_info['original_size']
            a4_x = roi_x_in_bg * 210 / bg_w
            a4_y = roi_y_in_bg * 297 / bg_h
            a4_w = roi_w_in_bg * 210 / bg_w
            a4_h = roi_h_in_bg * 297 / bg_h
        
        return {
            'x': a4_x, 'y': a4_y,
            'width': a4_w, 'height': a4_h
        }
    
    def check_roi_touches(self, touch_points, marker_positions):
        """檢查ROI觸碰 - 修正座標轉換"""
        touched_rois = []
        current_time = time.time()
        
        if not self.project_data or not marker_positions or len(marker_positions) < 3:
            return touched_rois
        
        for touch_point in touch_points:
            # 觸碰點轉A4座標
            a4_coord = self.pixel_to_a4_coordinate(touch_point, marker_positions)
            if not a4_coord:
                continue
                
            a4_x, a4_y = a4_coord
            
            # 檢查每個ROI
            for roi in self.project_data.get('rois', []):
                # ROI編輯器座標轉A4毫米座標
                roi_a4 = self.editor_roi_to_a4_mm(roi)
                
                # 檢查觸碰點是否在ROI內
                if (roi_a4['x'] <= a4_x <= roi_a4['x'] + roi_a4['width'] and
                    roi_a4['y'] <= a4_y <= roi_a4['y'] + roi_a4['height']):
                    
                    touched_rois.append(roi)
                    
                    # 播放音效 (防重複)
                    audio_file = roi.get('audio_file', '')
                    if audio_file and os.path.exists(audio_file):
                        roi_id = roi['id']
                        if roi_id not in self.audio_cooldowns or current_time - self.audio_cooldowns[roi_id] > 1.0:
                            self.play_audio(audio_file)
                            self.audio_cooldowns[roi_id] = current_time
                            print(f"🔊 Playing audio for ROI: {roi['name']} at A4({a4_x:.1f}, {a4_y:.1f})")
                            
        return touched_rois
    
    def play_audio(self, audio_file):
        try:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Audio playback error: {e}")
            
    def set_volume(self, value):
        self.volume = value / 100.0
        
    def stop_audio(self):
        pygame.mixer.music.stop()
        
    def update_frame(self):
        try:
            frames = self.pipeline.wait_for_frames(100)
            if not frames:
                return
            
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                return
            
            # Get images
            color_image = frame_to_bgr_image(color_frame)
            rgb_h, rgb_w = color_image.shape[:2]
            
            depth_w = depth_frame.get_width()
            depth_h = depth_frame.get_height()
            depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
            depth_image = depth_data.reshape((depth_h, depth_w))
            
            display_image = color_image.copy()
            
            # ArUco detection
            corners, ids, _ = cv2.aruco.detectMarkers(display_image, self.aruco_dict)
            marker_positions = {}
            marker_count = 0
            
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(display_image, corners, ids)
                
                for i, marker_id in enumerate(ids.flatten()):
                    if marker_id in [0, 1, 2, 3]:
                        center = np.mean(corners[i][0], axis=0).astype(int)
                        marker_positions[marker_id] = tuple(center)
                        marker_count += 1
                
                # Calibrate
                self.calibrate_plane(marker_positions, depth_image, (rgb_h, rgb_w), (depth_h, depth_w))
            
            # Hand detection and ROI checking
            touch_points = []
            if self.is_calibrated:
                rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_image)
                
                if results.multi_hand_landmarks:
                    for landmarks in results.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(display_image, landmarks, self.mp_hands.HAND_CONNECTIONS)
                        
                        finger_tip = landmarks.landmark[8]
                        rgb_x = int(finger_tip.x * rgb_w)
                        rgb_y = int(finger_tip.y * rgb_h)
                        
                        depth_x, depth_y = self.map_rgb_to_depth(rgb_x, rgb_y, (rgb_h, rgb_w), (depth_h, depth_w))
                        finger_depth = self.get_depth_at_point(depth_image, depth_x, depth_y)
                        
                        if finger_depth:
                            distance = abs(finger_depth - self.plane_depth) * 1000
                            
                            if distance < 25:  # TOUCH
                                color, status = (0, 0, 255), "TOUCH"
                                touch_points.append((rgb_x, rgb_y))
                            elif distance < 50:  # HOVER
                                color, status = (0, 165, 255), "HOVER"
                            else:  # FAR
                                color, status = (255, 0, 0), "FAR"
                            
                            cv2.circle(display_image, (rgb_x, rgb_y), 15, color, -1)
                            cv2.putText(display_image, f'{status}: {distance:.0f}mm', 
                                       (rgb_x + 20, rgb_y - 20),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Check ROI touches with corrected coordinate conversion
            touched_rois = self.check_roi_touches(touch_points, marker_positions)
            self.update_touched_list(touched_rois)
            
            # Draw status
            if self.is_calibrated:
                status_color = (0, 255, 0)
                status_text = f"CALIBRATED - Plane: {self.plane_depth*1000:.1f}mm"
            else:
                status_color = (0, 255, 255)
                progress = (self.calibration_count / 30) * 100
                status_text = f"CALIBRATING... {progress:.0f}%"
            
            cv2.putText(display_image, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            board_text = f"ArUco Board: {'✓' if marker_count >= 3 else '✗'} ({marker_count}/4)"
            cv2.putText(display_image, board_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if marker_count >= 3 else (0, 0, 255), 2)
            
            # Update UI
            self.update_status_ui(marker_count >= 3, marker_count, len(touch_points), len(touched_rois))
            self.display_image(display_image)
            
        except Exception as e:
            print(f"Frame update error: {e}")
    
    def update_status_ui(self, board_detected, marker_count, hand_count, roi_touches):
        self.board_status.setText(f"ArUco Board: {'✓' if board_detected else '✗'} ({marker_count}/4)")
        
        progress = (self.calibration_count / 30) * 100
        self.calibration_status.setText(f"Calibration: {progress:.0f}%")
        self.progress_bar.setValue(int(progress))
        
        self.hand_status.setText(f"Hand: {hand_count} detected")
        self.roi_status.setText(f"ROI Touches: {roi_touches}")
    
    def update_touched_list(self, touched_rois):
        self.touched_list.clear()
        for roi in touched_rois:
            audio_status = "🔊" if roi.get('audio_file') and os.path.exists(roi.get('audio_file', '')) else "🔇"
            self.touched_list.addItem(f"{roi['name']} {audio_status}")
    
    def display_image(self, image):
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        self.timer.stop()
        self.pipeline.stop()
        pygame.mixer.quit()
        event.accept()

def main():
    app = QApplication(sys.argv)
    detector = FixedROIDetector()
    detector.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()