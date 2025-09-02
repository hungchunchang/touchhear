# app.py - 主應用
from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import json
import uuid
from datetime import datetime
from detector import A4WebStreamDetector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROJECTS_FOLDER'] = 'projects'

# 確保資料夾存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROJECTS_FOLDER'], exist_ok=True)

detector = A4WebStreamDetector()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/editor')
def editor():
    return render_template('editor.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/video_feed')
def video_feed():
    return detector.get_video_stream()

@app.route('/api/detection-status')
def detection_status():
    return jsonify(detector.get_detection_results())

# 專案相關 API
@app.route('/api/projects', methods=['GET', 'POST'])
def api_projects():
    if request.method == 'GET':
        # 列出所有專案
        projects = []
        if os.path.exists(app.config['PROJECTS_FOLDER']):
            for folder in os.listdir(app.config['PROJECTS_FOLDER']):
                config_path = os.path.join(app.config['PROJECTS_FOLDER'], folder, 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        project = json.load(f)
                        project['id'] = folder
                        projects.append(project)
        return jsonify(projects)
    
    else:
        # 創建新專案
        data = request.get_json()
        project_id = str(uuid.uuid4())[:8]
        project_path = os.path.join(app.config['PROJECTS_FOLDER'], project_id)
        os.makedirs(project_path, exist_ok=True)
        
        project = {
            'name': data['name'],
            'created_at': datetime.now().isoformat(),
            'background_image': None,
            'rois': []
        }
        
        with open(os.path.join(project_path, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(project, f, ensure_ascii=False, indent=2)
        
        project['id'] = project_id
        return jsonify(project)

@app.route('/api/projects/<project_id>/upload', methods=['POST'])
def upload_background(project_id):
    file = request.files.get('image')
    if file:
        filename = f"bg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.split('.')[-1]}"
        project_path = os.path.join(app.config['PROJECTS_FOLDER'], project_id)
        file_path = os.path.join(project_path, filename)
        file.save(file_path)
        
        # 更新專案配置
        config_path = os.path.join(project_path, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['background_image'] = filename
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return jsonify({'filename': filename, 'success': True})
    
    return jsonify({'error': '無檔案'}), 400

@app.route('/api/projects/<project_id>/rois', methods=['POST'])
def add_roi(project_id):
    data = request.get_json()
    config_path = os.path.join(app.config['PROJECTS_FOLDER'], project_id, 'config.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    roi = {
        'id': str(uuid.uuid4()),
        'name': data['name'],
        'type': data['type'],
        'x': data['x'],
        'y': data['y'],
        'width': data.get('width'),
        'height': data.get('height'),
        'audio_file': None
    }
    
    config['rois'].append(roi)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return jsonify(roi)

@app.route('/projects/<project_id>/<filename>')
def project_file(project_id, filename):
    return send_from_directory(os.path.join(app.config['PROJECTS_FOLDER'], project_id), filename)

if __name__ == '__main__':
    print("啟動 A4 棋盤手勢檢測服務...")
    print("在瀏覽器開啟: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)