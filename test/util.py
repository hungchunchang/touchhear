import cv2
import numpy as np
import argparse

def generate_aruco_markers():
    # 創建 ArUco 字典
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    
    # 生成四個標記 (ID 0-3)
    marker_size = 200  # 像素
    
    for i in range(4):
        # 生成標記
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, i, marker_size)
        
        # 加上白邊框（列印時更清晰）
        border_size = 20
        bordered_img = cv2.copyMakeBorder(marker_img, border_size, border_size, 
                                        border_size, border_size, 
                                        cv2.BORDER_CONSTANT, value=255)
        
        # 儲存
        filename = f'aruco_marker_{i}.png'
        cv2.imwrite(filename, bordered_img)
        print(f'生成: {filename}')

def create_a4_layout_with_image(image_path=None):
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 200
    
    # A4 尺寸 (300 DPI)
    a4_width, a4_height = 2480, 3508
    layout = np.ones((a4_height, a4_width, 3), dtype=np.uint8) * 255
    
    # 標記位置（四角）
    positions = [
        (50, 50),                           # 左上
        (a4_width-marker_size-50, 50),      # 右上
        (a4_width-marker_size-50, a4_height-marker_size-50), # 右下
        (50, a4_height-marker_size-50)      # 左下
    ]
    
    # 計算地圖區域
    map_left = positions[0][0] + marker_size + 100
    map_right = positions[1][0] - 100
    map_top = positions[0][1] + marker_size + 100
    map_bottom = positions[3][1] - 100
    map_width = map_right - map_left
    map_height = map_bottom - map_top
    
    # 載入並縮放圖片
    if image_path:
        try:
            image = cv2.imread(image_path)
            if image is not None:
                h, w = image.shape[:2]
                
                # 計算縮放比例（保持長寬比）
                scale_w = map_width / w
                scale_h = map_height / h
                scale = min(scale_w, scale_h)
                
                # 縮放圖片
                new_w, new_h = int(w * scale), int(h * scale)
                resized_img = cv2.resize(image, (new_w, new_h))
                
                # 置中放置
                start_x = map_left + (map_width - new_w) // 2
                start_y = map_top + (map_height - new_h) // 2
                
                layout[start_y:start_y+new_h, start_x:start_x+new_w] = resized_img
                print(f'圖片已放置: {new_w}x{new_h} pixels')
            else:
                print(f'無法載入圖片: {image_path}')
        except Exception as e:
            print(f'處理圖片錯誤: {e}')
    
    # 放置 ArUco 標記
    for i, (x, y) in enumerate(positions):
        marker = cv2.aruco.generateImageMarker(aruco_dict, i, marker_size)
        marker_bgr = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        layout[y:y+marker_size, x:x+marker_size] = marker_bgr
        
        # 標記 ID 標籤
        cv2.putText(layout, f'ID:{i}', (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    
    # 繪製地圖區域框線（僅在無圖片時）
    if not image_path:
        cv2.rectangle(layout, (map_left, map_top), 
                     (map_right, map_bottom), (128,128,128), 3)
        cv2.putText(layout, 'Map Area', 
                   (map_left, map_top - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    
    output_name = 'a4_with_image.png' if image_path else 'a4_template.png'
    cv2.imwrite(output_name, layout)
    print(f'生成: {output_name}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='生成 ArUco 標記和 A4 模板')
    parser.add_argument('--image', '-i', help='要放置的圖片路徑')
    args = parser.parse_args()
    
    generate_aruco_markers()
    create_a4_layout_with_image(args.image)
    
    print("\n使用方法:")
    if args.image:
        print("1. 列印 a4_with_image.png")
    else:
        print("1. 列印 a4_template.png")
        print("2. 或用 python script.py --image your_map.jpg")
    print("3. 確保列印時保持實際尺寸")