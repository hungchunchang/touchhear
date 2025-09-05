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
    document.getElementById('board-status').textContent = 
        `棋盤: ${data.board ? '✓' : '✗'} (${data.detected_markers?.length || 0}/4)`;
    
    document.getElementById('hand-status').textContent = 
        `手部: ${data.hands?.length > 0 ? '✓' : '✗'}`;
    
    if (data.depth_reference !== undefined) {
        const progress = Math.round((data.calibration_progress || 0) * 100);
        document.getElementById('depth-status').textContent = 
            `深度: ${progress > 30 ? '已校準' : '校準中'} (${progress}%)`;
    } else {
        document.getElementById('depth-status').textContent = '深度: 標準模式';
    }
}

function updateDetailedInfo(data) {
    // 校準進度
    const calibrationProgress = document.getElementById('calibration-progress');
    if (calibrationProgress) {
        if (data.calibration_progress !== undefined) {
            const progress = Math.round(data.calibration_progress * 100);
            calibrationProgress.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <span style="margin-right: 10px;">校準進度:</span>
                    <div style="flex: 1; background: #e0e0e0; border-radius: 3px; height: 6px;">
                        <div style="width: ${progress}%; background: #007aff; height: 100%; border-radius: 3px;"></div>
                    </div>
                    <span style="margin-left: 10px;">${progress}%</span>
                </div>
            `;
            
            if (data.depth_reference) {
                calibrationProgress.innerHTML += `<small>基準深度: ${Math.round(data.depth_reference)}mm</small>`;
            }
        } else {
            calibrationProgress.innerHTML = '<small>標準檢測模式 (無深度感測)</small>';
        }
    }
    
    // 手指位置詳情 - 顯示 TOUCH/HOVER/FAR
    const fingerPositions = document.getElementById('finger-positions');
    if (fingerPositions && data.hands && data.hands.length > 0) {
        let html = '<div style="margin-top: 10px;"><strong>手指狀態:</strong></div>';
        
        data.hands.forEach((hand, index) => {
            const handNum = index + 1;
            let statusIcon = '🔵';
            let statusText = 'FAR';
            let statusColor = '#007aff';
            
            if (hand.contact_state === 'touch' || hand.is_touching) {
                statusIcon = '🔴';
                statusText = 'TOUCH';
                statusColor = '#ff3b30';
            } else if (hand.contact_state === 'hover') {
                statusIcon = '🟠';
                statusText = 'HOVER';
                statusColor = '#ff9500';
            }
            
            html += `<div style="font-size: 12px; margin: 3px 0; color: ${statusColor};">`;
            html += `${statusIcon} <strong>${statusText}</strong> - 手指 ${handNum}`;
            
            if (hand.finger_depth) {
                html += ` | 深度: ${Math.round(hand.finger_depth)}mm`;
            }
            
            if (hand.depth_diff !== undefined) {
                html += ` | 距離: ${Math.round(Math.abs(hand.depth_diff))}mm`;
            }
            
            if (hand.a4_coord) {
                html += ` | A4: (${hand.a4_coord[0]}, ${hand.a4_coord[1]})mm`;
            }
            
            html += `</div>`;
        });
        
        fingerPositions.innerHTML = html;
    } else {
        if (fingerPositions) {
            fingerPositions.innerHTML = '<small class="text-muted">無手部檢測</small>';
        }
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