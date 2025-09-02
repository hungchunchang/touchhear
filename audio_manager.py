# audio_manager.py - 音效管理模組
import pygame
import os
import threading
import time

class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.audio_cache = {}
        self.last_played = {}
        self.cooldown_time = 1.0  # 防止重複播放的冷卻時間
        
    def load_audio(self, audio_path):
        """載入音效檔案"""
        if audio_path not in self.audio_cache:
            if os.path.exists(audio_path):
                try:
                    self.audio_cache[audio_path] = pygame.mixer.Sound(audio_path)
                except pygame.error as e:
                    print(f"Failed to load audio {audio_path}: {e}")
                    return False
        return True
    
    def play_audio(self, audio_path, roi_id=None):
        """播放音效"""
        current_time = time.time()
        
        # 檢查冷卻時間
        if roi_id and roi_id in self.last_played:
            if current_time - self.last_played[roi_id] < self.cooldown_time:
                return False
        
        if self.load_audio(audio_path):
            try:
                self.audio_cache[audio_path].play()
                if roi_id:
                    self.last_played[roi_id] = current_time
                return True
            except pygame.error as e:
                print(f"Failed to play audio {audio_path}: {e}")
        
        return False
    
    def stop_all(self):
        """停止所有音效"""
        pygame.mixer.stop()
    
    def set_volume(self, volume):
        """設定音量 (0.0-1.0)"""
        pygame.mixer.music.set_volume(volume)
    
    def get_supported_formats(self):
        """取得支援的音效格式"""
        return ['.wav', '.mp3', '.ogg', '.m4a']