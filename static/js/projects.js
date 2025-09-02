// projects.js - 專案管理功能

class ProjectManager {
    constructor() {
        this.projects = [];
        this.init();
    }
    
    init() {
        this.loadProjects();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        document.getElementById('newProjectBtn').addEventListener('click', () => {
            this.createNewProject();
        });
    }
    
    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            this.projects = await response.json();
            this.renderProjects();
        } catch (error) {
            console.error('載入專案失敗:', error);
            this.showEmptyState();
        }
    }
    
    renderProjects() {
        const grid = document.getElementById('projectsGrid');
        const emptyState = document.getElementById('emptyState');
        
        if (this.projects.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        grid.innerHTML = '';
        
        this.projects.forEach(project => {
            const card = this.createProjectCard(project);
            grid.appendChild(card);
        });
    }
    
    createProjectCard(project) {
        const card = document.createElement('div');
        card.className = 'project-card';
        
        const previewImg = project.background_image 
            ? `<img src="/projects/${project.id}/${project.background_image}" alt="預覽">`
            : '<div class="no-preview">無圖片</div>';
        
        card.innerHTML = `
            <div class="project-preview">
                ${previewImg}
            </div>
            <div class="project-info">
                <h4>${project.name}</h4>
                <p>建立時間: ${new Date(project.created_at).toLocaleDateString()}</p>
                <p>ROI 數量: ${project.rois.length}</p>
            </div>
            <div class="project-actions">
                <button class="btn btn-primary" onclick="projectManager.editProject('${project.id}')">
                    編輯
                </button>
                <button class="btn btn-success" onclick="projectManager.playProject('${project.id}')">
                    播放
                </button>
                <button class="btn btn-danger" onclick="projectManager.deleteProject('${project.id}')">
                    刪除
                </button>
            </div>
        `;
        
        return card;
    }
    
    async createNewProject() {
        const name = prompt('專案名稱:');
        if (!name) return;
        
        try {
            const response = await fetch('/api/projects', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            const project = await response.json();
            
            if (project.id) {
                this.projects.push(project);
                this.renderProjects();
                window.showNotification('專案建立成功！', 'success');
                
                // 跳轉到編輯器
                setTimeout(() => {
                    window.location.href = '/editor';
                }, 1000);
            }
        } catch (error) {
            window.showNotification('建立專案失敗', 'error');
            console.error(error);
        }
    }
    
    editProject(projectId) {
        // 跳轉到編輯器並傳遞專案ID
        window.location.href = `/editor?project=${projectId}`;
    }
    
    playProject(projectId) {
        // 跳轉到播放頁面
        window.location.href = `/play?project=${projectId}`;
    }
    
    async deleteProject(projectId) {
        if (!confirm('確定要刪除此專案？此操作無法復原。')) return;
        
        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.projects = this.projects.filter(p => p.id !== projectId);
                this.renderProjects();
                window.showNotification('專案已刪除', 'success');
            }
        } catch (error) {
            window.showNotification('刪除失敗', 'error');
            console.error(error);
        }
    }
    
    showEmptyState() {
        document.getElementById('projectsGrid').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
    }
}

// 全局變量
let projectManager;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    projectManager = new ProjectManager();
});

// 全局函數
function createNewProject() {
    projectManager.createNewProject();
}