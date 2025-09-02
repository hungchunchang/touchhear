// navbar.js - 導航欄功能

class NavigationBar {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.highlightCurrentPage();
    }
    
    setupEventListeners() {
        // 新專案按鈕
        const newProjectBtn = document.getElementById('newProjectBtn');
        if (newProjectBtn) {
            newProjectBtn.addEventListener('click', this.showCreateProjectModal.bind(this));
        }
        
        // 移動端選單切換
        this.setupMobileMenu();
    }
    
    highlightCurrentPage() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-menu a');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }
    
    setupMobileMenu() {
        // 移動端選單功能（如果需要）
        const navbar = document.querySelector('.navbar');
        let lastScrollY = window.scrollY;
        
        window.addEventListener('scroll', () => {
            if (window.scrollY > lastScrollY && window.scrollY > 44) {
                navbar.style.transform = 'translateY(-100%)';
            } else {
                navbar.style.transform = 'translateY(0)';
            }
            lastScrollY = window.scrollY;
        });
    }
    
    showCreateProjectModal() {
        const name = prompt('請輸入專案名稱:');
        if (name) {
            this.createProject(name);
        }
    }
    
    async createProject(name) {
        try {
            const response = await fetch('/api/projects', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            const project = await response.json();
            
            if (project.id) {
                // 跳轉到編輯器
                window.location.href = '/editor';
                
                // 通知其他頁面新專案已創建
                if (window.editor) {
                    window.editor.loadProjects();
                }
            }
        } catch (error) {
            alert('建立專案失敗');
            console.error('建立專案錯誤:', error);
        }
    }
    
    // 顯示通知
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // 添加樣式
        notification.style.position = 'fixed';
        notification.style.top = '60px';
        notification.style.right = '20px';
        notification.style.padding = '12px 20px';
        notification.style.borderRadius = '8px';
        notification.style.zIndex = '1001';
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        notification.style.transition = 'all 0.3s ease';
        
        // 設定顏色
        if (type === 'success') {
            notification.style.background = '#30d158';
            notification.style.color = 'white';
        } else if (type === 'error') {
            notification.style.background = '#ff3b30';
            notification.style.color = 'white';
        } else {
            notification.style.background = '#007aff';
            notification.style.color = 'white';
        }
        
        document.body.appendChild(notification);
        
        // 動畫顯示
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // 3秒後自動移除
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// 全局導航實例
let navbar;

document.addEventListener('DOMContentLoaded', function() {
    navbar = new NavigationBar();
});

// 導出給其他腳本使用
window.NavigationBar = NavigationBar;
window.showNotification = (message, type) => {
    if (navbar) {
        navbar.showNotification(message, type);
    }
};