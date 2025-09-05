#!/usr/bin/env python3
import sys
import subprocess
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class FixedTouchHearLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("TouchHear System Launcher (Fixed)")
        self.setGeometry(300, 300, 500, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                padding: 20px;
                font-size: 16px;
                border-radius: 12px;
                margin: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0056b3;
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background-color: #004494;
            }
            QLabel {
                color: #1d1d1f;
                margin: 10px;
            }
            .title {
                font-size: 28px;
                font-weight: 600;
                color: #1d1d1f;
            }
            .subtitle {
                font-size: 16px;
                color: #86868b;
                font-weight: 400;
            }
            .info {
                font-size: 13px;
                color: #86868b;
                font-weight: 400;
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #007aff;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title section
        title_layout = QVBoxLayout()
        title = QLabel("🎯 TouchHear System")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("class", "title")
        title_layout.addWidget(title)
        
        subtitle = QLabel("Fixed Coordinate Mapping System v2.0")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setProperty("class", "subtitle")
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addSpacing(10)
        
        # Status check
        status_label = QLabel()
        status_text = self.check_system_status()
        status_label.setText(status_text)
        status_label.setProperty("class", "info")
        layout.addWidget(status_label)
        
        # Main buttons
        editor_btn = QPushButton("📝 ROI Editor (Fixed)\n• Create touch regions relative to background\n• Accurate coordinate mapping\n• Export corrected A4 templates")
        editor_btn.clicked.connect(self.launch_editor)
        editor_btn.setMinimumHeight(100)
        layout.addWidget(editor_btn)
        
        detector_btn = QPushButton("🔍 Touch Detector (Fixed)\n• Real-time touch detection\n• Corrected ROI coordinate mapping\n• Audio feedback with proper touch areas")
        detector_btn.clicked.connect(self.launch_detector)
        detector_btn.setMinimumHeight(100)
        layout.addWidget(detector_btn)
        
        # Secondary buttons
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("🧪 Test Audio")
        test_btn.clicked.connect(self.test_audio)
        test_btn.setMaximumHeight(50)
        button_layout.addWidget(test_btn)
        
        help_btn = QPushButton("❓ Help")
        help_btn.clicked.connect(self.show_help)
        help_btn.setMaximumHeight(50)
        button_layout.addWidget(help_btn)
        
        layout.addLayout(button_layout)
        
        # Info section
        info = QLabel(
            "🔧 Fixed Issues:\n"
            "• ROI coordinates now relative to background image\n"
            "• Proper scaling and offset calculations\n"
            "• Accurate A4 template coordinate mapping\n"
            "• Fixed audio playback for touch areas\n\n"
            "📋 Workflow: Editor → Print A4 → Detector\n"
            "🎯 Ensure Orbbec camera is connected!"
        )
        info.setProperty("class", "info")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def check_system_status(self):
        """檢查系統狀態"""
        status_items = []
        
        # 檢查必要檔案
        required_files = [
            ('fixed_roi_editor.py', '✅ ROI Editor'),
            ('fixed_roi_detector.py', '✅ Touch Detector'),
            ('utils.py', '✅ Orbbec Utils')
        ]
        
        for filename, description in required_files:
            if os.path.exists(filename):
                status_items.append(f"{description}")
            else:
                status_items.append(f"❌ Missing: {filename}")
        
        # 檢查資料夾
        folders = ['projects', 'templates', 'audio', 'backgrounds']
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                status_items.append(f"📁 Created: {folder}/")
            else:
                status_items.append(f"📁 Ready: {folder}/")
        
        return "System Status:\n" + "\n".join(status_items)
        
    def launch_editor(self):
        """啟動修正的ROI編輯器"""
        try:
            if os.path.exists("fixed_roi_editor.py"):
                subprocess.Popen([sys.executable, "fixed_roi_editor.py"])
                QMessageBox.information(self, "Launched", 
                    "✅ Fixed ROI Editor started!\n\n"
                    "Key improvements:\n"
                    "• ROIs now relative to background\n"
                    "• Proper coordinate scaling\n"
                    "• Accurate A4 template export")
            else:
                QMessageBox.critical(self, "Error", 
                    "❌ fixed_roi_editor.py not found!\n\n"
                    "Please ensure the fixed editor file is in the current directory.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch editor:\n{e}")
            
    def launch_detector(self):
        """啟動修正的觸碰檢測器"""
        try:
            if os.path.exists("fixed_roi_detector.py"):
                subprocess.Popen([sys.executable, "fixed_roi_detector.py"])
                QMessageBox.information(self, "Launched", 
                    "✅ Fixed Touch Detector started!\n\n"
                    "Key improvements:\n"
                    "• Correct ROI coordinate mapping\n"
                    "• Fixed audio playback\n"
                    "• Accurate touch area detection")
            else:
                QMessageBox.critical(self, "Error", 
                    "❌ fixed_roi_detector.py not found!\n\n"
                    "Please ensure the fixed detector file is in the current directory.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch detector:\n{e}")
            
    def test_audio(self):
        """測試音效系統"""
        try:
            import pygame
            pygame.mixer.init()
            
            # 創建測試音效檔案路徑
            audio_folder = "audio"
            test_files = []
            
            if os.path.exists(audio_folder):
                for file in os.listdir(audio_folder):
                    if file.lower().endswith(('.wav', '.mp3', '.ogg', '.m4a')):
                        test_files.append(os.path.join(audio_folder, file))
            
            if test_files:
                # 播放第一個找到的音效檔案
                pygame.mixer.music.load(test_files[0])
                pygame.mixer.music.play()
                QMessageBox.information(self, "Audio Test", 
                    f"🔊 Playing test audio:\n{os.path.basename(test_files[0])}\n\n"
                    f"Found {len(test_files)} audio files in audio/ folder.")
            else:
                QMessageBox.information(self, "Audio Test", 
                    "🔇 No audio files found in audio/ folder.\n\n"
                    "Please add some .wav, .mp3, .ogg, or .m4a files\n"
                    "to the audio/ folder for testing.")
                    
        except ImportError:
            QMessageBox.warning(self, "Audio Test", 
                "❌ pygame not installed.\n\n"
                "Please install pygame for audio support:\n"
                "pip install pygame")
        except Exception as e:
            QMessageBox.warning(self, "Audio Test", f"Audio test failed:\n{e}")
            
    def show_help(self):
        """顯示幫助資訊"""
        help_text = """
🎯 TouchHear System Fixed v2.0 Help

🔧 What's Fixed:
• ROI coordinates now properly relative to background images
• Accurate scaling and coordinate transformation
• Fixed audio playback when touching ROI areas
• Corrected A4 template generation

📋 Complete Workflow:

1. 📝 ROI Editor:
   • Load background image
   • Draw ROI rectangles ON the background
   • Assign audio files to ROIs
   • Save project (includes scaling info)
   • Export A4 template with corrected coordinates

2. 🖨️ Print Setup:
   • Print A4 template at ACTUAL SIZE (100%)
   • Ensure all 4 ArUco markers are visible
   • Place flat on surface in front of camera

3. 🔍 Touch Detector:
   • Load the same project file
   • Wait for ArUco calibration (3+ markers)
   • Wait for depth calibration (if using Orbbec)
   • Touch ROI areas to trigger audio

🎯 Key Requirements:
• Orbbec depth camera (recommended)
• Python packages: PyQt5, opencv-python, mediapipe, pygame, pyorbbecsdk
• Proper lighting for ArUco detection
• Stable camera mount

🔧 Troubleshooting:
• If audio doesn't play: Check file paths and pygame installation
• If ROIs don't trigger: Verify ArUco markers are detected
• If coordinates are wrong: Ensure template was exported with fixed editor
"""
        
        msg = QMessageBox()
        msg.setWindowTitle("TouchHear Help")
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

def main():
    app = QApplication(sys.argv)
    
    # 設定應用程式資訊
    app.setApplicationName("TouchHear Launcher Fixed")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("TouchHear")
    
    # 套用現代化風格
    app.setStyle('Fusion')
    
    launcher = FixedTouchHearLauncher()
    launcher.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()