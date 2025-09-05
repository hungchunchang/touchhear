#!/usr/bin/env python3
import sys
import json
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pygame

class ROICanvas(QLabel):
    roi_created = pyqtSignal(dict)
    roi_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet("border: 2px solid black; background: white;")
        self.setScaledContents(True)
        
        self.background_image = None
        self.rois = []
        self.selected_roi = None
        self.drawing = False
        self.start_pos = None
        
    def set_background(self, image_path):
        self.background_image = QPixmap(image_path)
        self.update_display()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.drawing = True
            
            # Check if clicking on existing ROI
            for roi in self.rois:
                if self.point_in_roi(event.pos(), roi):
                    self.selected_roi = roi
                    self.roi_selected.emit(roi)
                    self.update_display()
                    return
            
            self.selected_roi = None
            
    def mouseMoveEvent(self, event):
        if self.drawing and self.start_pos:
            self.current_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if self.drawing and self.start_pos:
            end_pos = event.pos()
            
            # Create new ROI
            x = min(self.start_pos.x(), end_pos.x())
            y = min(self.start_pos.y(), end_pos.y())
            w = abs(end_pos.x() - self.start_pos.x())
            h = abs(end_pos.y() - self.start_pos.y())
            
            if w > 10 and h > 10:  # Minimum size
                roi = {
                    'id': len(self.rois),
                    'name': f'ROI {len(self.rois) + 1}',
                    'x': x, 'y': y, 'width': w, 'height': h,
                    'audio_file': ''
                }
                self.rois.append(roi)
                self.roi_created.emit(roi)
                
        self.drawing = False
        self.start_pos = None
        self.update_display()
        
    def point_in_roi(self, point, roi):
        return (roi['x'] <= point.x() <= roi['x'] + roi['width'] and
                roi['y'] <= point.y() <= roi['y'] + roi['height'])
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw ROIs
        for roi in self.rois:
            if roi == self.selected_roi:
                painter.setPen(QPen(Qt.red, 3))
                painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
            else:
                painter.setPen(QPen(Qt.blue, 2))
                painter.setBrush(QBrush(QColor(0, 0, 255, 30)))
                
            painter.drawRect(roi['x'], roi['y'], roi['width'], roi['height'])
            
            # Draw label
            painter.setPen(QPen(Qt.black, 1))
            painter.drawText(roi['x'] + 5, roi['y'] + 15, roi['name'])
            
        # Draw current drawing
        if self.drawing and self.start_pos and hasattr(self, 'current_pos'):
            painter.setPen(QPen(Qt.green, 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())
            painter.drawRect(x, y, w, h)
            
    def update_display(self):
        if self.background_image:
            self.setPixmap(self.background_image.scaled(self.size(), Qt.KeepAspectRatio))
        self.update()
        
    def delete_selected_roi(self):
        if self.selected_roi:
            self.rois.remove(self.selected_roi)
            self.selected_roi = None
            self.update_display()
            
    def get_rois(self):
        return self.rois
        
    def load_rois(self, rois):
        self.rois = rois
        self.update_display()

class ROIEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_file = "project_config.json"
        self.setup_ui()
        self.setup_audio()
        self.load_project()
        
    def setup_ui(self):
        self.setWindowTitle("ROI Editor")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout()
        
        # Canvas
        self.canvas = ROICanvas()
        self.canvas.roi_created.connect(self.on_roi_created)
        self.canvas.roi_selected.connect(self.on_roi_selected)
        layout.addWidget(self.canvas, 2)
        
        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel, 1)
        
        central_widget.setLayout(layout)
        
        # Menu
        self.create_menu()
        
    def create_control_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Background image
        layout.addWidget(QLabel("Background Image:"))
        bg_btn = QPushButton("Load Background")
        bg_btn.clicked.connect(self.load_background)
        layout.addWidget(bg_btn)
        
        # ROI list
        layout.addWidget(QLabel("ROI List:"))
        self.roi_list = QListWidget()
        self.roi_list.itemClicked.connect(self.on_roi_list_clicked)
        layout.addWidget(self.roi_list)
        
        # ROI properties
        layout.addWidget(QLabel("ROI Properties:"))
        
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.update_roi_name)
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("Audio File:"))
        audio_layout = QHBoxLayout()
        self.audio_label = QLabel("No audio")
        audio_btn = QPushButton("Browse")
        audio_btn.clicked.connect(self.select_audio)
        audio_layout.addWidget(self.audio_label)
        audio_layout.addWidget(audio_btn)
        layout.addLayout(audio_layout)
        
        # Test audio
        test_btn = QPushButton("Test Audio")
        test_btn.clicked.connect(self.test_audio)
        layout.addWidget(test_btn)
        
        # Delete ROI
        delete_btn = QPushButton("Delete ROI")
        delete_btn.clicked.connect(self.delete_roi)
        layout.addWidget(delete_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('File')
        file_menu.addAction('New Project', self.new_project)
        file_menu.addAction('Open Project', self.open_project)
        file_menu.addAction('Save Project', self.save_project)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
        
    def setup_audio(self):
        pygame.mixer.init()
        
    def load_background(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Background Image", 
                                                  "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.canvas.set_background(file_path)
            self.background_path = file_path
            
    def on_roi_created(self, roi):
        self.update_roi_list()
        
    def on_roi_selected(self, roi):
        self.name_edit.setText(roi['name'])
        self.audio_label.setText(roi['audio_file'] or "No audio")
        
    def on_roi_list_clicked(self, item):
        roi_id = int(item.text().split(':')[0])
        for roi in self.canvas.get_rois():
            if roi['id'] == roi_id:
                self.canvas.selected_roi = roi
                self.canvas.update_display()
                self.on_roi_selected(roi)
                break
                
    def update_roi_name(self):
        if self.canvas.selected_roi:
            self.canvas.selected_roi['name'] = self.name_edit.text()
            self.update_roi_list()
            self.canvas.update_display()
            
    def select_audio(self):
        if not self.canvas.selected_roi:
            QMessageBox.warning(self, "Warning", "Please select a ROI first!")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File",
                                                  "", "Audio (*.wav *.mp3 *.ogg)")
        if file_path:
            self.canvas.selected_roi['audio_file'] = file_path
            self.audio_label.setText(os.path.basename(file_path))
            
    def test_audio(self):
        if self.canvas.selected_roi and self.canvas.selected_roi['audio_file']:
            try:
                pygame.mixer.music.load(self.canvas.selected_roi['audio_file'])
                pygame.mixer.music.play()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot play audio: {e}")
        else:
            QMessageBox.warning(self, "Warning", "No audio file selected!")
                
    def delete_roi(self):
        if self.canvas.selected_roi:
            reply = QMessageBox.question(self, "Confirm", "Delete selected ROI?", 
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.canvas.delete_selected_roi()
                self.update_roi_list()
                self.name_edit.clear()
                self.audio_label.setText("No audio")
        
    def update_roi_list(self):
        self.roi_list.clear()
        for roi in self.canvas.get_rois():
            audio_status = "🔊" if roi['audio_file'] else "🔇"
            self.roi_list.addItem(f"{roi['id']}: {roi['name']} {audio_status}")
            
    def new_project(self):
        self.canvas.rois.clear()
        self.canvas.selected_roi = None
        self.canvas.background_image = None
        self.canvas.update_display()
        self.update_roi_list()
        self.name_edit.clear()
        self.audio_label.setText("No audio")
        
    def save_project(self):
        data = {
            'background': getattr(self, 'background_path', ''),
            'rois': self.canvas.get_rois()
        }
        
        with open(self.project_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        QMessageBox.information(self, "Saved", "Project saved successfully!")
        
    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project",
                                                  "", "JSON (*.json)")
        if file_path:
            self.project_file = file_path
            self.load_project()
            
    def load_project(self):
        if os.path.exists(self.project_file):
            try:
                with open(self.project_file, 'r') as f:
                    data = json.load(f)
                    
                if data.get('background'):
                    if os.path.exists(data['background']):
                        self.canvas.set_background(data['background'])
                        self.background_path = data['background']
                    
                self.canvas.load_rois(data.get('rois', []))
                self.update_roi_list()
                
            except Exception as e:
                print(f"Error loading project: {e}")

def main():
    app = QApplication(sys.argv)
    editor = ROIEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()