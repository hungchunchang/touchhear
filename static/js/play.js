// 播放模式 JavaScript - 包含深度資訊顯示
let detectionInterval;
let audioContext;

function initializePlayMode() {
    // 初始化音效上下文
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // 開始檢測監控
    startDetectionMonitoring();
}

function startDetectionMonitoring() {
    detectionInterval = setInterval(updateDetectionAndAudio, 100); // 更頻繁的檢測
}

function updateDetectionAndAudio() {
    fetch('/api/detection-status')
        .then(response => response.json())
        .then(data => {
            updatePlayStatus(data);
            handleROITouches(data.roi_touches);
        })
        .catch(error => {
            console.error('Error fetching detection status:', error);
        });
}

function updatePlayStatus(data) {
    const boardStatus = document.getElementById('board-status');
    const handStatus = document.getElementById('hand-status');
    const touchStatus = document.getElementById('touch-status');
    
    if (boardStatus) {
        const markerCount = data.detected_markers ? data.detected_markers.length : 0;
        boardStatus.className = `badge ${data.board ? 'bg-success' : 'bg-danger'}`;
        boardStatus.textContent = `棋盤: ${data.board ? '✓' : '✗'} (${markerCount}/4)`;
    }
    
    if (handStatus) {
        const handCount = data.hands ? data.hands.length : 0;
        const touchingCount = data.hands ? data.hands.filter(h => h.contact_state === 'touch').length : 0;
        handStatus.className = `badge ${handCount > 0 ? 'bg-success' : 'bg-secondary'}`;
        handStatus.textContent = `手部: ${handCount > 0 ? '✓' : '✗'} (${touchingCount}/${handCount} 接觸)`;
    }
    
    if (touchStatus) {
        const touchCount = data.hands ? data.hands.filter(h => h.contact_state === 'touch').length : 0;
        const hoverCount = data.hands ? data.hands.filter(h => h.contact_state === 'hover').length : 0;
        const farCount = data.hands ? data.hands.filter(h => h.contact_state === 'far').length : 0;
        
        touchStatus.className = `badge ${touchCount > 0 ? 'bg-danger' : hoverCount > 0 ? 'bg-warning' : 'bg-secondary'}`;
        touchStatus.textContent = `🔴${touchCount} 🟠${hoverCount} 🔵${farCount}`;
    }
    
    // 更新手部詳細資訊
    updateHandDetails(data.hands || []);
}

function updateHandDetails(hands) {
    const handDetails = document.getElementById('hand-details');
    if (!handDetails) return;
    
    if (hands.length === 0) {
        handDetails.innerHTML = '<small class="text-muted">無手部檢測</small>';
        return;
    }
    
    let html = '';
    hands.forEach((hand, index) => {
        let statusIcon = '🔵';
        let statusText = 'FAR';
        let statusClass = 'text-primary';
        
        if (hand.contact_state === 'touch') {
            statusIcon = '🔴';
            statusText = 'TOUCH';
            statusClass = 'text-danger';
        } else if (hand.contact_state === 'hover') {
            statusIcon = '🟠';
            statusText = 'HOVER';
            statusClass = 'text-warning';
        }
        
        html += `<div class="hand-detail-item mb-2 p-2 border rounded">`;
        html += `<div class="${statusClass}"><strong>${statusIcon} ${statusText}</strong></div>`;
        
        if (hand.finger_depth) {
            html += `<small>深度: ${Math.round(hand.finger_depth)}mm</small><br>`;
        }
        
        if (hand.depth_diff !== undefined) {
            html += `<small>距離差: ${Math.round(Math.abs(hand.depth_diff))}mm</small><br>`;
        }
        
        if (hand.a4_coord) {
            html += `<small>A4: (${hand.a4_coord[0]}, ${hand.a4_coord[1]}) mm</small>`;
        }
        
        html += `</div>`;
    });
    
    handDetails.innerHTML = html;
}

function handleROITouches(touchedROIs) {
    const touchList = document.getElementById('touch-list');
    touchList.innerHTML = '';
    
    touchedROIs.forEach(roi => {
        const div = document.createElement('div');
        div.className = 'alert alert-success py-1 px-2 mb-1';
        div.innerHTML = `
            <i class="fas fa-hand-pointer"></i> ${roi.name}
            ${roi.audio_file ? '<i class="fas fa-volume-up text-success"></i>' : '<i class="fas fa-volume-mute text-muted"></i>'}
        `;
        touchList.appendChild(div);
        
        // 播放對應音效
        if (roi.audio_file) {
            playROIAudio(roi.id, roi.audio_file);
        }
    });
    
    if (touchedROIs.length === 0) {
        touchList.innerHTML = '<small class="text-muted">無觸碰</small>';
    }
}

function playROIAudio(roiId, audioFile) {
    fetch('/api/play-audio', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            roi_id: roiId,
            audio_file: audioFile
        })
    })
    .catch(error => {
        console.error('Error playing audio:', error);
    });
}

function setVolume(volume) {
    document.getElementById('volume-display').textContent = volume;
    
    fetch('/api/set-volume', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({volume: volume / 100})
    });
}

function stopAllAudio() {
    fetch('/api/stop-audio', {method: 'POST'});
}

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePlayMode();
});