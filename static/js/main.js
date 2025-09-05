// main.js - 支援深度檢測的前端邏輯

let detectionInterval;
let isMonitoring = false;
let lastDetectionData = {};

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('TouchHear 系統已啟動');
    startDetectionMonitoring();
}

function startDetectionMonitoring() {
    if (isMonitoring) return;
    
    isMonitoring = true;
    detectionInterval = setInterval(updateDetectionStatus, 500);
    console.log('檢測監控已啟動');
}

function stopDetectionMonitoring() {
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    isMonitoring = false;
    console.log('檢測監控已停止');
}

function updateDetectionStatus() {
    fetch('/api/detection-status')
        .then(response => response.json())
        .then(data => {
            lastDetectionData = data;
            updateStatusDisplay(data);
        })
        .catch(error => {
            console.error('獲取檢測狀態失敗:', error);
            showErrorStatus();
        });
}

function updateStatusDisplay(data) {
    // 更新棋盤狀態
    const boardStatus = document.getElementById('board-status');
    if (boardStatus) {
        const markerCount = data.detected_markers ? data.detected_markers.length : 0;
        boardStatus.className = `badge ${data.board ? 'bg-success' : 'bg-danger'}`;
        boardStatus.textContent = `棋盤: ${data.board ? '✓' : '✗'} (${markerCount}/4 標記)`;
    }
    
    // 更新手部狀態
    const handStatus = document.getElementById('hand-status');
    if (handStatus) {
        const handCount = data.hands ? data.hands.length : 0;
        handStatus.className = `badge ${handCount > 0 ? 'bg-success' : 'bg-secondary'}`;
        handStatus.textContent = `手部: ${handCount > 0 ? '✓' : '✗'} (${handCount})`;
    }
    
    // 更新深度校準狀態
    const depthStatus = document.getElementById('depth-status');
    if (depthStatus) {
        const calibrationProgress = data.calibration_progress || 0;
        const isCalibrated = calibrationProgress > 0.3;
        
        if (data.depth_reference !== undefined && data.depth_reference !== null) {
            depthStatus.className = `badge ${isCalibrated ? 'bg-info' : 'bg-warning'}`;
            const progress = Math.round(calibrationProgress * 100);
            const paperDepth = Math.round(data.depth_reference);
            depthStatus.textContent = `深度: ${isCalibrated ? '已校準' : '校準中'} (${progress}%) | 紙張: ${paperDepth}mm`;
        } else {
            depthStatus.className = 'badge bg-secondary';
            depthStatus.textContent = '深度: 標準模式';
        }
    }
    
    // 更新接觸狀態
    const touchStatus = document.getElementById('touch-status');
    if (touchStatus) {
        const touchCount = data.hands ? data.hands.filter(h => h.contact_state === 'touch').length : 0;
        const hoverCount = data.hands ? data.hands.filter(h => h.contact_state === 'hover').length : 0;
        const farCount = data.hands ? data.hands.filter(h => h.contact_state === 'far').length : 0;
        
        if (touchCount > 0) {
            touchStatus.className = 'badge bg-danger';
            touchStatus.textContent = `🔴 ${touchCount} 個接觸`;
        } else if (hoverCount > 0) {
            touchStatus.className = 'badge bg-warning';
            touchStatus.textContent = `🟠 ${hoverCount} 個懸停`;
        } else if (farCount > 0) {
            touchStatus.className = 'badge bg-primary';
            touchStatus.textContent = `🔵 ${farCount} 個遠距`;
        } else {
            touchStatus.className = 'badge bg-secondary';
            touchStatus.textContent = '接觸: 無';
        }
    }
    
    // 更新詳細資訊
    updateDetailedInfo(data);
}

function updateDetailedInfo(data) {
    // 校準進度
    const calibrationProgress = document.getElementById('calibration-progress');
    if (calibrationProgress) {
        if (data.calibration_progress !== undefined) {
            const progress = Math.round(data.calibration_progress * 100);
            calibrationProgress.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="margin-right: 10px; font-weight: 500;">校準進度:</span>
                    <div style="flex: 1; background: #e0e0e0; border-radius: 3px; height: 8px;">
                        <div style="width: ${progress}%; background: linear-gradient(90deg, #007aff, #30d158); height: 100%; border-radius: 3px; transition: width 0.3s ease;"></div>
                    </div>
                    <span style="margin-left: 10px; font-weight: 500;">${progress}%</span>
                </div>
            `;
            
            if (data.depth_reference) {
                calibrationProgress.innerHTML += `<small style="color: #666;">基準深度: ${Math.round(data.depth_reference)}mm</small>`;
            }
        } else {
            calibrationProgress.innerHTML = '<small style="color: #666;">標準檢測模式 (無深度感測)</small>';
        }
    }
    
    // 手指位置詳情
    const fingerPositions = document.getElementById('finger-positions');
    if (fingerPositions && data.hands && data.hands.length > 0) {
        let html = '<div style="margin-top: 15px;"><strong>手指詳情:</strong></div>';
        
        data.hands.forEach((hand, index) => {
            const handNum = index + 1;
            let statusIcon = '🔵';
            let statusText = 'FAR';
            let statusColor = '#007aff';
            let bgColor = '#f0f9ff';
            
            if (hand.contact_state === 'touch' || hand.is_touching) {
                statusIcon = '🔴';
                statusText = 'TOUCH';
                statusColor = '#ff3b30';
                bgColor = '#fff5f5';
            } else if (hand.contact_state === 'hover') {
                statusIcon = '🟠';
                statusText = 'HOVER';
                statusColor = '#ff9500';
                bgColor = '#fff8f0';
            }
            
            html += `<div style="background: ${bgColor}; border: 1px solid ${statusColor}; border-radius: 8px; padding: 10px; margin: 8px 0; font-size: 13px;">`;
            html += `<div style="color: ${statusColor}; font-weight: bold; margin-bottom: 4px;">${statusIcon} ${statusText} - 手指 ${handNum}</div>`;
            
            if (hand.finger_depth) {
                html += `<div>深度: <strong>${Math.round(hand.finger_depth)}mm</strong></div>`;
            }
            
            if (hand.depth_diff !== undefined) {
                html += `<div>距離差: <strong>${Math.round(Math.abs(hand.depth_diff))}mm</strong></div>`;
            }
            
            if (hand.a4_coord) {
                html += `<div>A4 座標: <strong>(${hand.a4_coord[0]}, ${hand.a4_coord[1]}) mm</strong></div>`;
            }
            
            html += `</div>`;
        });
        
        fingerPositions.innerHTML = html;
    } else {
        if (fingerPositions) {
            fingerPositions.innerHTML = '<div style="margin-top: 15px;"><small style="color: #666;">無手部檢測</small></div>';
        }
    }
}

function showErrorStatus() {
    const statusElements = ['board-status', 'hand-status', 'depth-status', 'touch-status'];
    statusElements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.className = 'badge bg-secondary';
            element.textContent = element.textContent.split(':')[0] + ': 連線錯誤';
        }
    });
}

// 工具函數
function formatCoordinate(coord) {
    if (!coord) return 'N/A';
    return `(${coord[0]}, ${coord[1]}) mm`;
}

function formatDepth(depth) {
    if (depth === undefined || depth === null) return 'N/A';
    return `${Math.round(depth)}mm`;
}

function getContactStateIcon(state) {
    switch (state) {
        case 'touch': return '🔴';
        case 'hover': return '🟠';
        case 'far': return '🔵';
        default: return '⚪';
    }
}

function getContactStateColor(state) {
    switch (state) {
        case 'touch': return '#ff3b30';
        case 'hover': return '#ff9500';
        case 'far': return '#007aff';
        default: return '#666';
    }
}

// 頁面生命週期管理
window.addEventListener('beforeunload', function() {
    stopDetectionMonitoring();
});

window.addEventListener('focus', function() {
    if (!isMonitoring) {
        startDetectionMonitoring();
    }
});

window.addEventListener('blur', function() {
    // 可選擇性暫停監控以節省資源
    // stopDetectionMonitoring();
});

// 錯誤處理
function handleError(error, context) {
    console.error(`${context} 錯誤:`, error);
}

// 導出函數供其他腳本使用
window.DetectionApp = {
    start: startDetectionMonitoring,
    stop: stopDetectionMonitoring,
    isRunning: () => isMonitoring,
    getLastData: () => lastDetectionData
};