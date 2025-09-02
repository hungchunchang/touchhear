# file_manager.py - 檔案管理模組
import json
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

class FileManager:
    def __init__(self, projects_folder):
        self.projects_folder = projects_folder
        os.makedirs(projects_folder, exist_ok=True)
    
    def list_projects(self):
        """列出所有專案"""
        projects = []
        if not os.path.exists(self.projects_folder):
            return projects
            
        for folder_name in os.listdir(self.projects_folder):
            project_path = os.path.join(self.projects_folder, folder_name)
            config_path = os.path.join(project_path, 'config.json')
            
            if os.path.isdir(project_path) and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        config['folder_name'] = folder_name
                        projects.append(config)
                except Exception as e:
                    print(f"Error loading project {folder_name}: {e}")
        
        return sorted(projects, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def create_project(self, name, background_image=None):
        """創建新專案"""
        folder_name = secure_filename(name) + '_' + str(uuid.uuid4())[:8]
        project_path = os.path.join(self.projects_folder, folder_name)
        os.makedirs(project_path, exist_ok=True)
        
        project_config = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'background_image': background_image,
            'rois': []
        }
        
        config_path = os.path.join(project_path, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(project_config, f, ensure_ascii=False, indent=2)
        
        project_config['folder_name'] = folder_name
        return project_config
    
    def load_project(self, project_name):
        """載入專案"""
        config_path = os.path.join(self.projects_folder, project_name, 'config.json')
        
        if not os.path.exists(config_path):        
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    config['folder_name'] = project_name
                    return config
            except Exception as e:
                print(f"Error loading project {project_name}: {e}")
                return None
    def export_project_image(self, project_name, canvas_width=800, canvas_height=600):
        """導出專案為圖片（背景+ROI）"""
        project = self.load_project(project_name)
        if not project:
            return None
        
        import cv2
        import numpy as np
        
        # 創建畫布
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
        
        # 載入背景圖片
        if project.get('background_image'):
            bg_path = os.path.join(self.projects_folder, project_name, project['background_image'])
            if os.path.exists(bg_path):
                bg_image = cv2.imread(bg_path)
                if bg_image is not None:
                    # 縮放背景圖片以適應畫布
                    bg_resized = cv2.resize(bg_image, (canvas_width, canvas_height))
                    canvas = bg_resized
        
        # 繪製 ROI
        for roi in project.get('rois', []):
            if roi['type'] == 'rectangle':
                # 將 A4 座標轉換為畫布座標
                x = int(roi['x'] * canvas_width / 210)
                y = int(roi['y'] * canvas_height / 297)
                w = int(roi['width'] * canvas_width / 210)
                h = int(roi['height'] * canvas_height / 297)
                
                # 繪製矩形
                cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 255, 0, 50), -1)
                
                # 繪製標籤
                cv2.putText(canvas, roi['name'], (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
            elif roi['type'] == 'circle':
                center_x = int((roi['x'] + roi['radius']) * canvas_width / 210)
                center_y = int((roi['y'] + roi['radius']) * canvas_height / 297)
                radius = int(roi['radius'] * min(canvas_width/210, canvas_height/297))
                
                # 繪製圓形
                cv2.circle(canvas, (center_x, center_y), radius, (0, 255, 0), 2)
                cv2.circle(canvas, (center_x, center_y), radius, (0, 255, 0, 50), -1)
                
                # 繪製標籤
                cv2.putText(canvas, roi['name'], 
                           (center_x - 20, center_y - radius - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 儲存導出圖片
        export_filename = f"{project['name']}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        export_path = os.path.join(self.projects_folder, project_name, export_filename)
        
        success = cv2.imwrite(export_path, canvas)
        return export_filename if success else None
    
    def save_project(self, project_name, config):
        """儲存專案"""
        config_path = os.path.join(self.projects_folder, project_name, 'config.json')
        
        # 移除 folder_name，因為這不應該存在配置文件中
        save_config = config.copy()
        save_config.pop('folder_name', None)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving project {project_name}: {e}")
            return False
    
    def delete_project(self, project_name):
        """刪除專案"""
        project_path = os.path.join(self.projects_folder, project_name)
        
        try:
            import shutil
            shutil.rmtree(project_path)
            return True
        except Exception as e:
            print(f"Error deleting project {project_name}: {e}")
            return False
    
    def add_roi(self, project_name, roi_data):
        """新增 ROI"""
        config = self.load_project(project_name)
        if not config:
            return None
        
        roi_id = str(uuid.uuid4())
        roi = {
            'id': roi_id,
            'type': roi_data['type'],  # 'rectangle' or 'circle'
            'x': roi_data['x'],
            'y': roi_data['y'],
            'name': roi_data.get('name', f"ROI {len(config['rois']) + 1}"),
            'audio_file': roi_data.get('audio_file', ''),
            'created_at': datetime.now().isoformat()
        }
        
        # 根據類型添加特定屬性
        if roi['type'] == 'rectangle':
            roi['width'] = roi_data['width']
            roi['height'] = roi_data['height']
        elif roi['type'] == 'circle':
            roi['radius'] = roi_data['radius']
        
        config['rois'].append(roi)
        
        if self.save_project(project_name, config):
            return roi
        return None
    
    def update_roi(self, project_name, roi_id, roi_data):
        """更新 ROI"""
        config = self.load_project(project_name)
        if not config:
            return None
        
        for i, roi in enumerate(config['rois']):
            if roi['id'] == roi_id:
                # 更新屬性
                roi.update(roi_data)
                roi['modified_at'] = datetime.now().isoformat()
                
                if self.save_project(project_name, config):
                    return roi
                break
        
        return None
    
    def delete_roi(self, project_name, roi_id):
        """刪除 ROI"""
        config = self.load_project(project_name)
        if not config:
            return False
        
        config['rois'] = [roi for roi in config['rois'] if roi['id'] != roi_id]
        
        return self.save_project(project_name, config)
    
    def save_uploaded_file(self, file, project_name=None):
        """儲存上傳的檔案"""
        if file and file.filename:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            if project_name:
                # 儲存到專案資料夾
                project_path = os.path.join(self.projects_folder, project_name)
                file_path = os.path.join(project_path, filename)
            else:
                # 儲存到上傳資料夾
                from flask import current_app
                upload_folder = current_app.config['UPLOAD_FOLDER']
                file_path = os.path.join(upload_folder, filename)
            
            file.save(file_path)
            return filename
        
        return None