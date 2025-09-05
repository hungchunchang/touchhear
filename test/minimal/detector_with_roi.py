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

class ROIDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_detector()
        self.setup_audio()
        self.load_project()
        self.setup_timer()
        
    def setup_ui(self):
        self.setWindowTitle("ROI Touch Detector")
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
        layout.addWidget(QLabel("ROI List:"))
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
        
        # ROI data
        self.rois = []
        self.background_image = None
        
    def setup_audio(self):
        pygame.mixer.init()
        self.audio_cooldowns = {}
        self.volume = 0.7
        
    def load_project(self):
        project_file = "project_config.json"
        if os.path.exists(project_file):
            try:
                with open(project_file, 'r') as f:
                    data = json.load(f)
                    
                self.rois = data.get('rois', [])
                bg_path = data.get('background', '')
                
                if bg_path and os.path.exists(bg_path):
                    self.background_image = cv2.imread(bg_path)
                    
                self.update_roi_list()
                print(f"Loaded {len(self.rois)} ROIs")
                
            except Exception as e:
                print(f"Error loading project: {e}")
                
    def load_project_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                self.rois = data.get('rois', [])
                bg_path = data.get('background', '')
                
                if bg_path and os.path.exists(bg_path):
                    self.background_image = cv2.imread(bg_path)
                    
                self.update_roi_list()
                QMessageBox.information(self, "Success", f"Loaded {len(self.rois)} ROIs")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load project: {e}")
                
    def update_roi_list(self):
        self.roi_list.clear()
        for roi in self.rois:
            audio_status = "🔊" if roi.get('audio_file') else "🔇"
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
    
    def check_roi_touches(self, touch_points, marker_positions):
        """Check which ROIs are being touched - supports A4 coordinate mapping"""
        touched_rois = []
        current_time = time.time()
        
        if not marker_positions or len(marker_positions) < 3:
            return touched_rois
        
        # A4 template content area parameters (consistent with aruco_generator.py)
        a4_width, a4_height = 2480, 3508
        marker_size = 150
        margin = 30
        
        content_left = margin + marker_size + 50
        content_right = a4_width - marker_size - margin - 50
        content_top = margin + marker_size + 50
        content_bottom = a4_height - marker_size - margin - 50
        content_width = content_right - content_left
        content_height = content_bottom - content_top
        
        for touch_point in touch_points:
            # Convert touch point from camera coordinates to A4 coordinates
            a4_coord = self.pixel_to_a4_coordinate(touch_point, marker_positions)
            if not a4_coord:
                continue
                
            a4_x, a4_y = a4_coord
            
            # Check each ROI
            for roi in self.rois:
                # Map ROI from editor coordinates to A4 template coordinates
                roi_x = content_left + (roi['x'] * content_width / 800)  # Editor width 800px
                roi_y = content_top + (roi['y'] * content_height / 600)   # Editor height 600px
                roi_w = roi['width'] * content_width / 800
                roi_h = roi['height'] * content_height / 600
                
                # Convert A4 coordinates to mm (A4 template coordinates to actual size)
                # A4 actual size: 210mm x 297mm
                real_roi_x = roi_x * 210 / a4_width
                real_roi_y = roi_y * 297 / a4_height
                real_roi_w = roi_w * 210 / a4_width
                real_roi_h = roi_h * 297 / a4_height
                
                # Check if touch point is inside ROI
                if (real_roi_x <= a4_x <= real_roi_x + real_roi_w and
                    real_roi_y <= a4_y <= real_roi_y + real_roi_h):
                    
                    touched_rois.append(roi)
                    
                    # Play audio (prevent duplicate)
                    if roi.get('audio_file') and os.path.exists(roi['audio_file']):
                        roi_id = roi['id']
                        if roi_id not in self.audio_cooldowns or current_time - self.audio_cooldowns[roi_id] > 1.0:
                            self.play_audio(roi['audio_file'])
                            self.audio_cooldowns[roi_id] = current_time
                            print(f"🔊 Playing audio for ROI: {roi['name']}")
                            
        return touched_rois
    
    def pixel_to_a4_coordinate(self, pixel_pos, marker_positions):
        """Convert pixel coordinates to A4 coordinates - returns mm units"""
        if not marker_positions or len(marker_positions) < 3:
            return None
        
        # A4 size (mm)
        a4_width_mm = 210
        a4_height_mm = 297
        margin_mm = 3  # ~3mm margin
        
        marker_refs = {
            0: [margin_mm, margin_mm],                                    # top left
            1: [a4_width_mm - margin_mm, margin_mm],                     # top right
            2: [a4_width_mm - margin_mm, a4_height_mm - margin_mm],      # bottom right
            3: [margin_mm, a4_height_mm - margin_mm]                     # bottom left
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
            
            # Draw background ROIs if available
            if self.background_image is not None:
                bg_resized = cv2.resize(self.background_image, (rgb_w, rgb_h))
                display_image = cv2.addWeighted(display_image, 0.7, bg_resized, 0.3, 0)
            
            # Draw ROIs
            for roi in self.rois:
                cv2.rectangle(display_image, 
                             (roi['x'], roi['y']), 
                             (roi['x'] + roi['width'], roi['y'] + roi['height']),
                             (0, 255, 0), 2)
                cv2.putText(display_image, roi['name'],
                           (roi['x'], roi['y'] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
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
            
            # Check ROI touches
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
            audio_status = "🔊" if roi.get('audio_file') else "🔇"
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
    detector = ROIDetector()
    detector.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()