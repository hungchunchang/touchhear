#!/usr/bin/env python3
import sys
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class TouchHearLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("TouchHear System Launcher")
        self.setGeometry(300, 300, 400, 300)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial, sans-serif;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px;
                font-size: 16px;
                border-radius: 8px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QLabel {
                color: #333;
                font-size: 18px;
                font-weight: bold;
                margin: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🎯 TouchHear System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; color: #2c3e50; margin: 20px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Choose your tool:")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Buttons
        editor_btn = QPushButton("📝 ROI Editor\n• Create touch regions\n• Assign audio files\n• Generate A4 templates")
        editor_btn.clicked.connect(self.launch_editor)
        layout.addWidget(editor_btn)
        
        detector_btn = QPushButton("🔍 Touch Detector\n• Real-time touch detection\n• Audio feedback\n• A4 template support")
        detector_btn.clicked.connect(self.launch_detector)
        layout.addWidget(detector_btn)
        
        # Info
        info = QLabel("📋 Workflow: Editor → Print A4 → Detector\n🎯 Make sure your Orbbec camera is connected!")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size: 12px; color: #666; font-weight: normal;")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def launch_editor(self):
        try:
            subprocess.Popen([sys.executable, "roi_editor.py"])
            QMessageBox.information(self, "Launched", "ROI Editor started successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch ROI Editor:\n{e}")
            
    def launch_detector(self):
        try:
            subprocess.Popen([sys.executable, "detector_with_roi.py"])
            QMessageBox.information(self, "Launched", "Touch Detector started successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch Touch Detector:\n{e}")

def main():
    app = QApplication(sys.argv)
    launcher = TouchHearLauncher()
    launcher.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()