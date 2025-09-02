# app.py - 基礎Flask應用
from flask import Flask, render_template_string, jsonify
from detector import A4WebStreamDetector

app = Flask(__name__)
detector = A4WebStreamDetector()

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>A4 棋盤手勢檢測</title>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: Arial; 
                text-align: center; 
                background: #f0f0f0; 
                margin: 0;
                padding: 20px;
            }
            .container { 
                max-width: 900px; 
                margin: 0 auto; 
                padding: 20px; 
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            img { 
                border: 3px solid #333; 
                border-radius: 10px; 
                max-width: 100%;
                height: auto;
            }
            .status { 
                margin: 20px 0; 
                padding: 15px; 
                background: #f8f9fa; 
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }
            .instructions {
                text-align: left;
                background: #fff3cd;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
            }
            h1 { color: #333; margin-bottom: 10px; }
            .marker-info {
                background: #d1ecf1;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #17a2b8;
                margin: 10px 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 A4 棋盤手勢檢測系統</h1>
            <img src="/video_feed" width="640" height="480">
            
            <div class="instructions">
                <h3>📋 使用說明：</h3>
                <ol>
                    <li>列印 A4 模板（包含四個角落的 ArUco 標記）</li>
                    <li>將 A4 紙平放在攝影機前</li>
                    <li>用食指指向 A4 紙上的位置</li>
                    <li>系統會顯示手指在 A4 紙上的精確座標（單位：mm）</li>
                    <li>只有手指接觸紙面時才會記錄座標（陰影檢測）</li>
                </ol>
            </div>
            
            <div class="marker-info">
                <strong>ArUco 標記說明：</strong><br>
                • ID0 (左上角) • ID1 (右上角) • ID2 (右下角) • ID3 (左下角)<br>
                至少需要檢測到 3 個標記才能進行座標計算
            </div>
            
            <div class="status">
                <h3>💡 檢測狀態</h3>
                <p>即時影像中會顯示：</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>ArUco 標記檢測狀態（✓/✗）</li>
                    <li>手部檢測狀態</li>
                    <li>接觸檢測（紅圈=接觸，藍圈=懸空）</li>
                    <li>手指在 A4 紙上的精確位置 (mm)</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/video_feed')
def video_feed():
    return detector.get_video_stream()

@app.route('/api/detection-status')
def detection_status():
    return jsonify(detector.get_detection_results())

if __name__ == '__main__':
    print("啟動 A4 棋盤手勢檢測服務...")
    print("在瀏覽器開啟: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)