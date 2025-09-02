// main.js - 前端邏輯

// 全局變量
let detectionInterval;
let isMonitoring = false;

// DOM 元素載入完成後執行
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化應用
function initializeApp() {
    console.log('A4 檢測系統已啟動');
    startDetectionMonitoring();
}

// 開始監控檢測狀態
function startDetectionMonitoring() {
    if (isMonitoring) return;
    
    isMonitoring = true;
    detectionInterval = setInterval(updateDetectionStatus, 1000);
    console.log('檢測監控已啟動');
}

// 停止監控檢測狀態
function stopDetectionMonitoring() {
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    isMonitoring = false;
    console.log('檢測監控已停止');
}

// 更新檢測狀態
function updateDetectionStatus() {
    fetch('/api/detection-status')
        .then(response => response.json())
        .then(data => {
            console.log('檢測狀態:', data);
            // 這裡可以加入狀態顯示邏輯
            updateStatusDisplay(data);
        })
        .catch(error => {
            console.error('獲取檢測狀態失敗:', error);
        });
}

// 更新狀態顯示
function updateStatusDisplay(data) {
    // 如果有狀態顯示元素，可以在這裡更新
    // 目前檢測狀態直接顯示在視頻流中
    
    if (data.board) {
        console.log(`棋盤已檢測 (${data.detected_markers.length}/4 標記)`);
    }
    
    if (data.hands && data.hands.length > 0) {
        console.log(`檢測到 ${data.hands.length} 個手部`);
        
        // 如果有接觸檢測
        data.hands.forEach((hand, index) => {
            if (hand.a4_coord) {
                console.log(`手指 ${index + 1} 位置: (${hand.a4_coord[0]}, ${hand.a4_coord[1]}) mm`);
            }
        });
    }
}

// 頁面離開時清理
window.addEventListener('beforeunload', function() {
    stopDetectionMonitoring();
});

// 視窗獲得/失去焦點時暫停/恢復監控
window.addEventListener('focus', function() {
    if (!isMonitoring) {
        startDetectionMonitoring();
    }
});

window.addEventListener('blur', function() {
    // 可以選擇在失去焦點時暫停監控以節省資源
    // stopDetectionMonitoring();
});

// 工具函數
function formatCoordinate(coord) {
    if (!coord) return 'N/A';
    return `(${coord[0]}, ${coord[1]}) mm`;
}

function formatMarkerStatus(markers) {
    return `${markers.length}/4 標記`;
}

// 錯誤處理
function handleError(error, context) {
    console.error(`${context} 錯誤:`, error);
}

// 導出函數供其他腳本使用
window.DetectionApp = {
    start: startDetectionMonitoring,
    stop: stopDetectionMonitoring,
    isRunning: () => isMonitoring
};