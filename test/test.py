import cv2
import numpy as np
import mediapipe as mp

class ChessboardHandDetector:
    def __init__(self):
        # MediaPipe 手部檢測初始化
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # 棋盤參數 (8x8 內部角點)
        self.chessboard_size = (7, 7)
        
    def detect_chessboard(self, image):
        """檢測棋盤位置"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, self.chessboard_size, None)
        
        if ret:
            # 精細化角點
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            # 繪製棋盤
            cv2.drawChessboardCorners(image, self.chessboard_size, corners, ret)
            
        return ret, corners, image
    
    def detect_hands(self, image):
        """使用 MediaPipe 檢測手部"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_image)
        
        hand_landmarks = []
        
        if results.multi_hand_landmarks:
            for hand_landmark in results.multi_hand_landmarks:
                # 繪製手部關鍵點
                self.mp_drawing.draw_landmarks(
                    image, hand_landmark, self.mp_hands.HAND_CONNECTIONS)
                
                # 提取指尖位置 (食指指尖: landmark 8)
                h, w, _ = image.shape
                finger_tip = hand_landmark.landmark[8]
                finger_pos = (int(finger_tip.x * w), int(finger_tip.y * h))
                hand_landmarks.append(finger_pos)
                
                # 標記指尖位置
                cv2.circle(image, finger_pos, 10, (0, 255, 0), -1)
                cv2.putText(image, 'Finger Tip', 
                           (finger_pos[0] + 15, finger_pos[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return hand_landmarks, image
    
    def pixel_to_board_coordinate(self, pixel_pos, corners):
        """將像素座標轉換為棋盤座標"""
        if corners is None or len(corners) < 49:
            return None
            
        # 定義棋盤四個角點 (7x7 格子的四個角)
        top_left = corners[0][0]
        top_right = corners[6][0] 
        bottom_right = corners[48][0]
        bottom_left = corners[42][0]
        
        # 計算相對位置
        corner_points = np.float32([top_left, top_right, bottom_right, bottom_left])
        board_points = np.float32([[0, 0], [8, 0], [8, 8], [0, 8]])
        
        # 透視變換
        matrix = cv2.getPerspectiveTransform(corner_points, board_points * 100)
        pixel_array = np.float32([[pixel_pos]])
        board_coord = cv2.perspectiveTransform(pixel_array, matrix)
        
        x, y = board_coord[0][0]
        board_x, board_y = int(x // 100), int(y // 100)
        
        # 確保座標在棋盤範圍內
        if 0 <= board_x < 8 and 0 <= board_y < 8:
            return (board_x, board_y)
        return None

def main():
    detector = ChessboardHandDetector()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("無法開啟攝影機")
        return
    
    print("按 'q' 鍵退出程式")
    print("請將棋盤放在攝影機前")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 複製原始幀用於處理
        display_frame = frame.copy()
        
        # 檢測棋盤
        board_detected, corners, display_frame = detector.detect_chessboard(display_frame)
        
        # 檢測手部
        hand_positions, display_frame = detector.detect_hands(display_frame)
        
        # 顯示檢測狀態
        status_text = "棋盤: " + ("✓" if board_detected else "✗")
        cv2.putText(display_frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if board_detected else (0, 0, 255), 2)
        
        hand_text = f"手部: {'✓' if hand_positions else '✗'}"
        cv2.putText(display_frame, hand_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hand_positions else (0, 0, 255), 2)
        
        # 如果同時檢測到棋盤和手指，計算棋盤座標
        if board_detected and hand_positions:
            for finger_pos in hand_positions:
                board_coord = detector.pixel_to_board_coordinate(finger_pos, corners)
                if board_coord:
                    coord_text = f"棋盤位置: {board_coord}"
                    cv2.putText(display_frame, coord_text, (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # 顯示畫面
        cv2.imshow('棋盤手勢檢測', display_frame)
        
        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()