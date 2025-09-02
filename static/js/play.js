// 播放模式 JavaScript
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
        boardStatus.className = `badge ${data.board ? 'bg-success' : 'bg-danger'}`;
        boardStatus.textContent = `棋盤: ${data.board ? '✓' : '✗'} (${data.detected_markers.length}/4)`;
    }
    
    if (handStatus) {
        handStatus.className = `badge ${data.hands.length > 0 ? 'bg-success' : 'bg-secondary'}`;
        handStatus.textContent = `手部: ${data.hands.length > 0 ? '✓' : '✗'}`;
    }
    
    if (touchStatus) {
        touchStatus.className = `badge ${data.roi_touches.length > 0 ? 'bg-warning' : 'bg-secondary'}`;
        touchStatus.textContent = `ROI 觸碰: ${data.roi_touches.length}`;
    }
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