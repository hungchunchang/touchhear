import cv2
import numpy as np

def generate_aruco_markers():
    """生成單獨的 ArUco 標記"""
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 200
    
    for i in range(4):
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, i, marker_size)
        border_size = 20
        bordered_img = cv2.copyMakeBorder(marker_img, border_size, border_size, 
                                        border_size, border_size, 
                                        cv2.BORDER_CONSTANT, value=255)
        filename = f'aruco_marker_{i}.png'
        cv2.imwrite(filename, bordered_img)
        print(f'生成: {filename}')

def create_a4_template_with_rois(image_path=None, rois=None, output_path='a4_template.png'):
    """創建包含圖片、ROI 和 ArUco 的 A4 模板"""
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 150  # 稍微小一點的標記
    
    # A4 尺寸 (300 DPI)
    a4_width, a4_height = 2480, 3508
    layout = np.ones((a4_height, a4_width, 3), dtype=np.uint8) * 255
    
    # ArUco 標記位置（四角）
    margin = 30
    positions = [
        (margin, margin),                                    # 左上
        (a4_width-marker_size-margin, margin),              # 右上
        (a4_width-marker_size-margin, a4_height-marker_size-margin), # 右下
        (margin, a4_height-marker_size-margin)              # 左下
    ]
    
    # 計算內容區域
    content_left = positions[0][0] + marker_size + 50
    content_right = positions[1][0] - 50
    content_top = positions[0][1] + marker_size + 50
    content_bottom = positions[3][1] - 50
    content_width = content_right - content_left
    content_height = content_bottom - content_top
    
    # 載入並縮放背景圖片
    if image_path:
        try:
            image = cv2.imread(image_path)
            if image is not None:
                h, w = image.shape[:2]
                
                # 計算縮放比例（保持長寬比）
                scale_w = content_width / w
                scale_h = content_height / h
                scale = min(scale_w, scale_h)
                
                # 縮放圖片
                new_w, new_h = int(w * scale), int(h * scale)
                resized_img = cv2.resize(image, (new_w, new_h))
                
                # 置中放置
                start_x = content_left + (content_width - new_w) // 2
                start_y = content_top + (content_height - new_h) // 2
                
                layout[start_y:start_y+new_h, start_x:start_x+new_w] = resized_img
                print(f'背景圖片已放置: {new_w}x{new_h} pixels')
        except Exception as e:
            print(f'處理圖片錯誤: {e}')
    
    # 繪製 ROI 區域
    if rois:
        for roi in rois:
            # 將 ROI 座標映射到 A4 模板
            roi_x = content_left + int(roi['x'] * content_width / 800)  # 假設編輯器是 800px 寬
            roi_y = content_top + int(roi['y'] * content_height / 600)  # 假設編輯器是 600px 高
            roi_w = int(roi['width'] * content_width / 800)
            roi_h = int(roi['height'] * content_height / 600)
            
            # 繪製 ROI 矩形（半透明）
            overlay = layout.copy()
            cv2.rectangle(overlay, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), 
                         (0, 255, 0), -1)
            layout = cv2.addWeighted(layout, 0.8, overlay, 0.2, 0)
            
            # 繪製邊框
            cv2.rectangle(layout, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), 
                         (0, 255, 0), 3)
            
            # 添加 ROI 標籤
            label = roi.get('name', f"ROI {roi['id']}")
            audio_icon = " 🔊" if roi.get('audio_file') else ""
            full_label = label + audio_icon
            
            # 標籤背景
            label_size = cv2.getTextSize(full_label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            cv2.rectangle(layout, (roi_x, roi_y - 30), 
                         (roi_x + label_size[0] + 10, roi_y), (255, 255, 255), -1)
            cv2.rectangle(layout, (roi_x, roi_y - 30), 
                         (roi_x + label_size[0] + 10, roi_y), (0, 255, 0), 2)
            
            # 標籤文字
            cv2.putText(layout, full_label, (roi_x + 5, roi_y - 8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    # 放置 ArUco 標記
    for i, (x, y) in enumerate(positions):
        marker = cv2.aruco.generateImageMarker(aruco_dict, i, marker_size)
        marker_bgr = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        layout[y:y+marker_size, x:x+marker_size] = marker_bgr
        
        # 標記 ID 標籤
        cv2.putText(layout, f'ID:{i}', (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,0), 3)
    
    # 添加標題和說明
    title = "TouchHear Interactive Template"
    cv2.putText(layout, title, (a4_width//2 - 300, 80), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,0), 3)
    
    # 說明文字
    instructions = [
        "1. Print this template at actual size (A4)",
        "2. Place flat in front of camera",
        "3. Touch green ROI areas to trigger audio",
        f"Generated ROIs: {len(rois) if rois else 0}"
    ]
    
    for i, instruction in enumerate(instructions):
        cv2.putText(layout, instruction, (content_left, a4_height - 150 + i*30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)
    
    # 儲存
    cv2.imwrite(output_path, layout)
    print(f'A4 模板已生成: {output_path}')
    return output_path

if __name__ == "__main__":
    generate_aruco_markers()
    create_a4_template_with_rois()