// editor.js - 編輯器功能

class ROIEditor {
    constructor() {
        this.canvas = document.getElementById('editorCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.currentProject = null;
        this.backgroundImage = null;
        this.rois = [];
        this.selectedROI = null;
        this.currentTool = 'select';
        this.isDrawing = false;
        this.startPos = {x: 0, y: 0};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadProjects();
    }
    
    setupEventListeners() {
        // Canvas 事件
        this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
        
        // 工具選擇
        document.querySelectorAll('input[name="tool"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentTool = e.target.value;
                this.canvas.style.cursor = e.target.value === 'select' ? 'default' : 'crosshair';
            });
        });
        
        // 專案選擇
        document.getElementById('projectSelect').addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadProject(e.target.value);
            }
        });
        
        // 背景圖片上傳
        document.getElementById('imageUpload').addEventListener('change', (e) => {
            if (e.target.files[0]) {
                this.loadBackgroundImage(e.target.files[0]);
            }
        });
        
        // 按鈕事件
        document.getElementById('createProjectBtn').addEventListener('click', () => {
            this.createProject();
        });
        
        document.getElementById('saveBtn').addEventListener('click', () => {
            this.saveProject();
        });
        
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportProject();
        });
        
        // Modal 事件
        document.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal();
        });
        
        document.getElementById('saveRoiBtn').addEventListener('click', () => {
            this.saveROI();
        });
        
        document.getElementById('deleteRoiBtn').addEventListener('click', () => {
            this.deleteROI();
        });
    }
    
    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const projects = await response.json();
            
            const select = document.getElementById('projectSelect');
            select.innerHTML = '<option value="">選擇專案...</option>';
            
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                option.textContent = project.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('載入專案失敗:', error);
        }
    }
    
    async createProject() {
        const name = prompt('專案名稱:');
        if (!name) return;
        
        try {
            const response = await fetch('/api/projects', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            const project = await response.json();
            this.loadProjects();
            document.getElementById('projectSelect').value = project.id;
            this.loadProject(project.id);
        } catch (error) {
            alert('建立專案失敗');
            console.error(error);
        }
    }
    
    async loadProject(projectId) {
        this.currentProject = projectId;
        this.rois = [];
        this.selectedROI = null;
        this.updateROIList();
        this.redraw();
    }
    
    loadBackgroundImage(file) {
        if (!this.currentProject) {
            alert('請先選擇專案');
            return;
        }
        
        const formData = new FormData();
        formData.append('image', file);
        
        fetch(`/api/projects/${this.currentProject}/upload`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const img = new Image();
                img.onload = () => {
                    this.backgroundImage = img;
                    this.redraw();
                    
                    // 顯示預覽
                    const preview = document.getElementById('imagePreview');
                    preview.innerHTML = `<img src="/projects/${this.currentProject}/${data.filename}" alt="背景圖片">`;
                };
                img.src = `/projects/${this.currentProject}/${data.filename}`;
            }
        })
        .catch(error => {
            alert('上傳失敗');
            console.error(error);
        });
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.startPos = {x, y};
        this.isDrawing = true;
        
        if (this.currentTool === 'select') {
            this.selectROI(x, y);
        }
    }
    
    onMouseMove(e) {
        if (!this.isDrawing || this.currentTool === 'select') return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.redraw();
        this.drawPreview(x, y);
    }
    
    onMouseUp(e) {
        if (!this.isDrawing || this.currentTool === 'select') {
            this.isDrawing = false;
            return;
        }
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.currentTool === 'rectangle') {
            this.createRectangleROI(x, y);
        }
        
        this.isDrawing = false;
    }
    
    drawPreview(endX, endY) {
        this.ctx.strokeStyle = '#ff6600';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        if (this.currentTool === 'rectangle') {
            const width = endX - this.startPos.x;
            const height = endY - this.startPos.y;
            this.ctx.strokeRect(this.startPos.x, this.startPos.y, width, height);
        }
        
        this.ctx.setLineDash([]);
    }
    
    createRectangleROI(endX, endY) {
        const x = Math.min(this.startPos.x, endX);
        const y = Math.min(this.startPos.y, endY);
        const width = Math.abs(endX - this.startPos.x);
        const height = Math.abs(endY - this.startPos.y);
        
        if (width < 10 || height < 10) return; // 避免太小的ROI
        
        const roi = {
            name: `ROI ${this.rois.length + 1}`,
            type: 'rectangle',
            x: x,
            y: y,
            width: width,
            height: height
        };
        
        this.addROI(roi);
    }
    
    async addROI(roi) {
        if (!this.currentProject) {
            alert('請先選擇專案');
            return;
        }
        
        try {
            const response = await fetch(`/api/projects/${this.currentProject}/rois`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(roi)
            });
            
            const savedROI = await response.json();
            this.rois.push(savedROI);
            this.updateROIList();
            this.redraw();
        } catch (error) {
            alert('新增 ROI 失敗');
            console.error(error);
        }
    }
    
    selectROI(x, y) {
        this.selectedROI = null;
        
        // 從後往前檢查（最上層優先）
        for (let i = this.rois.length - 1; i >= 0; i--) {
            const roi = this.rois[i];
            
            if (roi.type === 'rectangle') {
                if (x >= roi.x && x <= roi.x + roi.width &&
                    y >= roi.y && y <= roi.y + roi.height) {
                    this.selectedROI = roi;
                    break;
                }
            }
        }
        
        this.updateROIList();
        this.redraw();
        
        // 如果選中ROI，顯示編輯modal
        if (this.selectedROI) {
            this.showROIModal();
        }
    }
    
    redraw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 繪製背景圖片
        if (this.backgroundImage) {
            this.ctx.drawImage(this.backgroundImage, 0, 0, this.canvas.width, this.canvas.height);
        }
        
        // 繪製所有ROI
        this.rois.forEach(roi => {
            this.drawROI(roi);
        });
    }
    
    drawROI(roi) {
        const isSelected = roi === this.selectedROI;
        
        this.ctx.strokeStyle = isSelected ? '#ff3b30' : '#007aff';
        this.ctx.lineWidth = isSelected ? 3 : 2;
        this.ctx.fillStyle = isSelected ? 'rgba(255, 59, 48, 0.2)' : 'rgba(0, 122, 255, 0.2)';
        
        if (roi.type === 'rectangle') {
            this.ctx.fillRect(roi.x, roi.y, roi.width, roi.height);
            this.ctx.strokeRect(roi.x, roi.y, roi.width, roi.height);
        }
        
        // 繪製標籤
        this.ctx.fillStyle = isSelected ? '#ff3b30' : '#007aff';
        this.ctx.font = '14px -apple-system, BlinkMacSystemFont, sans-serif';
        this.ctx.fillText(roi.name, roi.x + 5, roi.y - 5);
    }
    
    updateROIList() {
        const list = document.getElementById('roiList');
        list.innerHTML = '';
        
        this.rois.forEach(roi => {
            const div = document.createElement('div');
            div.className = `roi-item ${roi === this.selectedROI ? 'selected' : ''}`;
            div.onclick = () => {
                this.selectedROI = roi;
                this.updateROIList();
                this.redraw();
            };
            
            div.innerHTML = `
                <h5>${roi.name}</h5>
                <p>${roi.type} - (${Math.round(roi.x)}, ${Math.round(roi.y)})</p>
                ${roi.audio_file ? '<p>🔊 已設定音效</p>' : '<p>🔇 無音效</p>'}
            `;
            
            list.appendChild(div);
        });
    }
    
    showROIModal() {
        if (!this.selectedROI) return;
        
        document.getElementById('roiName').value = this.selectedROI.name;
        document.getElementById('roiModal').style.display = 'block';
    }
    
    closeModal() {
        document.getElementById('roiModal').style.display = 'none';
    }
    
    saveROI() {
        if (!this.selectedROI) return;
        
        const newName = document.getElementById('roiName').value;
        this.selectedROI.name = newName;
        
        // 處理音效上傳
        const audioFile = document.getElementById('audioUpload').files[0];
        if (audioFile) {
            this.uploadAudio(audioFile);
        }
        
        this.updateROIList();
        this.redraw();
        this.closeModal();
    }
    
    async uploadAudio(file) {
        const formData = new FormData();
        formData.append('audio', file);
        formData.append('roi_id', this.selectedROI.id);
        
        try {
            const response = await fetch(`/api/projects/${this.currentProject}/upload-audio`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (result.success) {
                this.selectedROI.audio_file = result.filename;
                alert('音效上傳成功！');
            }
        } catch (error) {
            alert('音效上傳失敗');
            console.error(error);
        }
    }
    
    deleteROI() {
        if (!this.selectedROI || !confirm('確定刪除此 ROI？')) return;
        
        this.rois = this.rois.filter(roi => roi !== this.selectedROI);
        this.selectedROI = null;
        this.updateROIList();
        this.redraw();
        this.closeModal();
    }
    
    async exportProject() {
        if (!this.currentProject) {
            alert('請先選擇專案');
            return;
        }
        
        try {
            const response = await fetch(`/api/projects/${this.currentProject}/export`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({width: 800, height: 600})
            });
            
            const result = await response.json();
            if (result.success) {
                // 自動下載
                const link = document.createElement('a');
                link.href = result.download_url;
                link.download = result.filename;
                link.click();
                
                alert('專案已匯出！');
            }
        } catch (error) {
            alert('匯出失敗');
            console.error(error);
        }
    }
    
    saveProject() {
        if (!this.currentProject) {
            alert('請先選擇專案');
            return;
        }
        
        alert('專案已儲存！');
    }
}

// 初始化編輯器
let editor;
document.addEventListener('DOMContentLoaded', function() {
    editor = new ROIEditor();
});