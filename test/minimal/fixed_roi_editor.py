#!/usr/bin/env python3
import sys
import json
import os
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pygame

# Import ArUco generator (ensure this file exists)
try:
    from aruco_generator import create_a4_template_with_rois
except ImportError:
    print("Warning: aruco_generator.py not found. A4 export will not work.")
    def create_a4_template_with_rois(*args, **kwargs):
        raise ImportError("aruco_generator module not available")

class ROICanvas(QLabel):
    roi_created = pyqtSignal(dict)
    roi_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setFixedSize(800, 600)
        self.setStyleSheet("border: 2px solid black; background: white;")
        self.setScaledContents(False)
        
        self.background_image = None
        self.rois = []
        self.selected_roi = None
        self.drawing = False
        self.start_pos = None
        
    def set_background(self, image_path):
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)
        self.background_image_path = image_path
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.drawing = True
            
            for roi in self.rois:
                if self.point_in_roi(event.pos(), roi):
                    self.selected_roi = roi
                    self.roi_selected.emit(roi)
                    self.update()
                    return
            
            self.selected_roi = None
            
    def mouseMoveEvent(self, event):
        if self.drawing and self.start_pos:
            self.current_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if self.drawing and self.start_pos:
            end_pos = event.pos()
            
            x = min(self.start_pos.x(), end_pos.x())
            y = min(self.start_pos.y(), end_pos.y())
            w = abs(end_pos.x() - self.start_pos.x())
            h = abs(end_pos.y() - self.start_pos.y())
            
            if w > 20 and h > 20:
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
        self.update()
        
    def point_in_roi(self, point, roi):
        return (roi['x'] <= point.x() <= roi['x'] + roi['width'] and
                roi['y'] <= point.y() <= roi['y'] + roi['height'])
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        for roi in self.rois:
            if roi == self.selected_roi:
                painter.setPen(QPen(Qt.red, 3))
                painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
            else:
                painter.setPen(QPen(Qt.green, 2))
                painter.setBrush(QBrush(QColor(0, 255, 0, 30)))
                
            painter.drawRect(roi['x'], roi['y'], roi['width'], roi['height'])
            
            painter.setPen(QPen(Qt.black, 1))
            label = roi['name']
            if roi.get('audio_file'):
                label += " 🔊"
            painter.drawText(roi['x'] + 5, roi['y'] + 15, label)
            
        if self.drawing and self.start_pos and hasattr(self, 'current_pos'):
            painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())
            painter.drawRect(x, y, w, h)
            
    def delete_selected_roi(self):
        if self.selected_roi:
            self.rois.remove(self.selected_roi)
            for i, roi in enumerate(self.rois):
                roi['id'] = i
            self.selected_roi = None
            self.update()
            
    def get_rois(self):
        return self.rois
        
    def load_rois(self, rois):
        self.rois = rois
        self.update()

class ROIEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_file = None
        self.background_image_path = None
        self.project_modified = False
        self.setup_ui()
        self.setup_audio()
        self.create_default_folders()
        
    def create_default_folders(self):
        folders = ['projects', 'templates', 'audio', 'backgrounds']
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            
    def mark_modified(self):
        self.project_modified = True
        self.update_window_title()
        
    def update_window_title(self):
        title = "TouchHear ROI Editor"
        if self.project_file:
            filename = os.path.basename(self.project_file)
            title += f" - {filename}"
        if self.project_modified:
            title += " *"
        self.setWindowTitle(title)
        
    def setup_ui(self):
        self.setWindowTitle("TouchHear ROI Editor")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout()
        
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout()
        canvas_layout.addWidget(QLabel("Canvas (Draw ROIs with mouse):"))
        
        self.canvas = ROICanvas()
        self.canvas.roi_created.connect(self.on_roi_created)
        self.canvas.roi_selected.connect(self.on_roi_selected)
        canvas_layout.addWidget(self.canvas)
        canvas_widget.setLayout(canvas_layout)
        
        layout.addWidget(canvas_widget, 2)
        
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel, 1)
        
        central_widget.setLayout(layout)
        self.create_menu()
        
    def create_control_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Background image section
        bg_group = QGroupBox("Background Image")
        bg_layout = QVBoxLayout()
        
        bg_btn = QPushButton("📁 Load Background Image")
        bg_btn.clicked.connect(self.load_background)
        bg_layout.addWidget(bg_btn)
        
        self.bg_label = QLabel("No background image")
        self.bg_label.setStyleSheet("color: gray; font-style: italic;")
        bg_layout.addWidget(self.bg_label)
        
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # ROI list section
        roi_group = QGroupBox("ROI List")
        roi_layout = QVBoxLayout()
        
        self.roi_list = QListWidget()
        self.roi_list.itemClicked.connect(self.on_roi_list_clicked)
        roi_layout.addWidget(self.roi_list)
        
        roi_group.setLayout(roi_layout)
        layout.addWidget(roi_group)
        
        # ROI properties section
        props_group = QGroupBox("ROI Properties")
        props_layout = QVBoxLayout()
        
        props_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.update_roi_name)
        self.name_edit.setPlaceholderText("Enter ROI name...")
        props_layout.addWidget(self.name_edit)
        
        props_layout.addWidget(QLabel("Audio File:"))
        audio_layout = QHBoxLayout()
        self.audio_label = QLabel("No audio")
        self.audio_label.setStyleSheet("color: gray; font-style: italic;")
        audio_btn = QPushButton("🎵 Browse")
        audio_btn.clicked.connect(self.select_audio)
        audio_layout.addWidget(self.audio_label)
        audio_layout.addWidget(audio_btn)
        props_layout.addLayout(audio_layout)
        
        # Audio controls
        audio_controls = QHBoxLayout()
        test_btn = QPushButton("▶️ Test")
        test_btn.clicked.connect(self.test_audio)
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_audio)
        audio_controls.addWidget(test_btn)
        audio_controls.addWidget(clear_btn)
        props_layout.addLayout(audio_controls)
        
        props_group.setLayout(props_layout)
        layout.addWidget(props_group)
        
        # ROI management
        mgmt_group = QGroupBox("ROI Management")
        mgmt_layout = QVBoxLayout()
        
        delete_btn = QPushButton("🗑️ Delete Selected ROI")
        delete_btn.clicked.connect(self.delete_roi)
        delete_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        mgmt_layout.addWidget(delete_btn)
        
        clear_all_btn = QPushButton("🧹 Clear All ROIs")
        clear_all_btn.clicked.connect(self.clear_all_rois)
        clear_all_btn.setStyleSheet("QPushButton { background-color: #ffa726; color: white; }")
        mgmt_layout.addWidget(clear_all_btn)
        
        mgmt_group.setLayout(mgmt_layout)
        layout.addWidget(mgmt_group)
        
        # Export section
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout()
        
        export_btn = QPushButton("📄 Generate A4 Template")
        export_btn.clicked.connect(self.export_a4_template)
        export_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        export_layout.addWidget(export_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('File')
        file_menu.addAction('🆕 New Project', self.new_project, 'Ctrl+N')
        file_menu.addAction('📂 Open Project', self.open_project, 'Ctrl+O')
        file_menu.addSeparator()
        file_menu.addAction('💾 Save Project', self.save_project, 'Ctrl+S')
        file_menu.addAction('💾 Save As...', self.save_project_as, 'Ctrl+Shift+S')
        file_menu.addSeparator()
        file_menu.addAction('📄 Export A4 Template', self.export_a4_template, 'Ctrl+E')
        file_menu.addSeparator()
        file_menu.addAction('❌ Exit', self.close, 'Ctrl+Q')
        
        help_menu = menubar.addMenu('Help')
        help_menu.addAction('ℹ️ About', self.show_about)
        help_menu.addAction('❓ Usage', self.show_usage)
        
    def setup_audio(self):
        pygame.mixer.init()
        
    def load_background(self):
        start_dir = "backgrounds" if os.path.exists("backgrounds") else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.canvas.set_background(file_path)
            self.background_image_path = file_path
            self.bg_label.setText(f"📷 {os.path.basename(file_path)}")
            self.bg_label.setStyleSheet("color: green;")
            self.mark_modified()
            
    def on_roi_created(self, roi):
        self.update_roi_list()
        self.mark_modified()
        
    def on_roi_selected(self, roi):
        self.name_edit.setText(roi['name'])
        if roi['audio_file']:
            self.audio_label.setText(f"🎵 {os.path.basename(roi['audio_file'])}")
            self.audio_label.setStyleSheet("color: green;")
        else:
            self.audio_label.setText("No audio")
            self.audio_label.setStyleSheet("color: gray; font-style: italic;")
            
    def on_roi_list_clicked(self, item):
        try:
            roi_id = int(item.text().split(':')[0])
            for roi in self.canvas.get_rois():
                if roi['id'] == roi_id:
                    self.canvas.selected_roi = roi
                    self.canvas.update()
                    self.on_roi_selected(roi)
                    break
        except:
            pass
                
    def update_roi_name(self):
        if self.canvas.selected_roi:
            self.canvas.selected_roi['name'] = self.name_edit.text()
            self.update_roi_list()
            self.canvas.update()
            self.mark_modified()
            
    def select_audio(self):
        if not self.canvas.selected_roi:
            QMessageBox.warning(self, "Warning", "Please select a ROI first!")
            return
            
        start_dir = "audio" if os.path.exists("audio") else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", start_dir,
            "Audio (*.wav *.mp3 *.ogg *.m4a)")
        if file_path:
            self.canvas.selected_roi['audio_file'] = file_path
            self.audio_label.setText(f"🎵 {os.path.basename(file_path)}")
            self.audio_label.setStyleSheet("color: green;")
            self.update_roi_list()
            self.canvas.update()
            self.mark_modified()
            
    def clear_audio(self):
        if self.canvas.selected_roi:
            self.canvas.selected_roi['audio_file'] = ''
            self.audio_label.setText("No audio")
            self.audio_label.setStyleSheet("color: gray; font-style: italic;")
            self.update_roi_list()
            self.canvas.update()
            self.mark_modified()
            
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
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Delete ROI '{self.canvas.selected_roi['name']}'?", 
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.canvas.delete_selected_roi()
                self.update_roi_list()
                self.name_edit.clear()
                self.audio_label.setText("No audio")
                self.audio_label.setStyleSheet("color: gray; font-style: italic;")
                self.mark_modified()
                
    def clear_all_rois(self):
        if self.canvas.rois:
            reply = QMessageBox.question(
                self, "Confirm Clear All", 
                f"Delete all {len(self.canvas.rois)} ROIs?", 
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.canvas.rois.clear()
                self.canvas.selected_roi = None
                self.canvas.update()
                self.update_roi_list()
                self.name_edit.clear()
                self.audio_label.setText("No audio")
                self.audio_label.setStyleSheet("color: gray; font-style: italic;")
                self.mark_modified()
        
    def update_roi_list(self):
        self.roi_list.clear()
        for roi in self.canvas.get_rois():
            audio_status = "🔊" if roi['audio_file'] else "🔇"
            self.roi_list.addItem(f"{roi['id']}: {roi['name']} {audio_status}")
            
    def new_project(self):
        if self.canvas.rois or self.background_image_path:
            reply = QMessageBox.question(
                self, "New Project", 
                "Create new project? Current work will be lost.", 
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
        self.canvas.rois.clear()
        self.canvas.selected_roi = None
        self.canvas.setPixmap(QPixmap())
        self.background_image_path = None
        self.canvas.update()
        self.update_roi_list()
        self.name_edit.clear()
        self.audio_label.setText("No audio")
        self.audio_label.setStyleSheet("color: gray; font-style: italic;")
        self.bg_label.setText("No background image")
        self.bg_label.setStyleSheet("color: gray; font-style: italic;")
        self.project_file = None
        self.project_modified = False
        self.update_window_title()
        
    def save_project(self):
        if self.project_file:
            self.save_to_file(self.project_file)
        else:
            self.save_project_as()
            
    def save_project_as(self):
        start_dir = "projects" if os.path.exists("projects") else ""
        default_name = os.path.join(start_dir, "new_project.json")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", default_name, "JSON (*.json)")
        if file_path:
            self.save_to_file(file_path)
            
    def save_to_file(self, file_path):
        data = {
            'background': self.background_image_path or '',
            'rois': self.canvas.get_rois(),
            'created_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.project_file = file_path
            self.project_modified = False
            self.update_window_title()
            
            rel_path = os.path.relpath(file_path)
            roi_count = len(self.canvas.rois)
            audio_count = sum(1 for roi in self.canvas.rois if roi.get('audio_file'))
            
            QMessageBox.information(self, "Project Saved", 
                f"✅ Project saved successfully!\n\n"
                f"📁 File: {rel_path}\n"
                f"📋 ROIs: {roi_count}\n"
                f"🔊 With audio: {audio_count}")
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{e}")
            
    def open_project(self):
        if self.project_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                "Current project has unsaved changes. Continue?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
        start_dir = "projects" if os.path.exists("projects") else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", start_dir, "JSON (*.json)")
        if file_path:
            self.load_project_from_file(file_path)
            
    def load_project_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            bg_path = data.get('background', '')
            if bg_path:
                if os.path.isabs(bg_path):
                    full_bg_path = bg_path
                else:
                    project_dir = os.path.dirname(file_path)
                    full_bg_path = os.path.join(project_dir, bg_path)
                    
                if os.path.exists(full_bg_path):
                    self.canvas.set_background(full_bg_path)
                    self.background_image_path = bg_path
                    self.bg_label.setText(f"📷 {os.path.basename(bg_path)}")
                    self.bg_label.setStyleSheet("color: green;")
                else:
                    self.bg_label.setText(f"❌ Missing: {os.path.basename(bg_path)}")
                    self.bg_label.setStyleSheet("color: red;")
                
            rois = data.get('rois', [])
            self.canvas.load_rois(rois)
            self.update_roi_list()
            
            self.project_file = file_path
            self.project_modified = False
            self.update_window_title()
            
            QMessageBox.information(self, "Project Loaded", 
                f"✅ Project loaded successfully!\n\n"
                f"📁 File: {os.path.basename(file_path)}\n"
                f"📋 ROIs: {len(rois)}\n"
                f"🔊 With audio: {sum(1 for roi in rois if roi.get('audio_file'))}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load project:\n{e}")
            
    def export_a4_template(self):
        if not self.canvas.rois:
            QMessageBox.warning(self, "Warning", "No ROIs to export! Please create some ROIs first.")
            return
            
        start_dir = "templates" if os.path.exists("templates") else ""
        project_name = "template"
        if self.project_file:
            project_name = os.path.splitext(os.path.basename(self.project_file))[0] + "_template"
        default_name = os.path.join(start_dir, f"{project_name}.png")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export A4 Template", default_name, "PNG (*.png)")
        
        if file_path:
            try:
                create_a4_template_with_rois(
                    image_path=self.background_image_path,
                    rois=self.canvas.get_rois(),
                    output_path=file_path
                )
                
                rel_path = os.path.relpath(file_path)
                roi_count = len(self.canvas.rois)
                audio_count = sum(1 for roi in self.canvas.rois if roi.get('audio_file'))
                
                QMessageBox.information(self, "Template Exported", 
                    f"🎯 A4 template exported successfully!\n\n"
                    f"📁 File: {rel_path}\n"
                    f"📋 ROIs: {roi_count}\n"
                    f"🔊 With audio: {audio_count}\n\n"
                    f"📄 Print this template at actual size (A4)\n"
                    f"🎯 Use with TouchHear detector for interaction!")
                
                reply = QMessageBox.question(self, "Open Template", 
                    "Open the exported template?", 
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        os.startfile(file_path)
                    except:
                        import subprocess
                        try:
                            subprocess.run(['xdg-open', file_path])
                        except:
                            try:
                                subprocess.run(['open', file_path])
                            except:
                                pass
                    
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export template:\n{e}")
                
    def closeEvent(self, event):
        if self.project_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                "Project has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                
            if reply == QMessageBox.Save:
                if self.project_file:
                    self.save_to_file(self.project_file)
                else:
                    self.save_project_as()
                    if self.project_modified:
                        event.ignore()
                        return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
                
        event.accept()
        
    def show_about(self):
        QMessageBox.about(self, "About TouchHear ROI Editor", 
            "TouchHear ROI Editor v1.0\n\n"
            "Create interactive touch regions with audio feedback.\n\n"
            "Features:\n"
            "• Visual ROI creation with mouse\n"
            "• Audio file assignment\n"
            "• A4 template generation with ArUco markers\n"
            "• Project save/load functionality\n\n"
            "Developed for touch-based interactive experiences.")
    
    def show_usage(self):
        QMessageBox.information(self, "How to Use", 
            "1. 📁 Load a background image (optional)\n"
            "2. 🖱️ Drag mouse to create ROI rectangles\n"
            "3. 📝 Click ROI to select and edit name\n"
            "4. 🎵 Assign audio files to ROIs\n"
            "5. 💾 Save your project\n"
            "6. 📄 Export A4 template for printing\n"
            "7. 🖨️ Print template at actual size\n"
            "8. 🎯 Use with TouchHear detector for interaction!\n\n"
            "Tips:\n"
            "• ROIs must be at least 20x20 pixels\n"
            "• Supported audio: WAV, MP3, OGG, M4A\n"
            "• Template includes ArUco markers for calibration")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    app.setApplicationName("TouchHear ROI Editor")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("TouchHear")
    
    editor = ROIEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()