import sys
import os
import random
import time
import numpy as np
import audioread
import librosa
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QSlider, QStyle, QFrame
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, QTime, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from pydub import AudioSegment

# 修正 np.float 和 np.complex 問題
if not hasattr(np, 'float'):
    np.float = np.float64
if not hasattr(np, 'complex'):
    np.complex = np.complex128

# 使用 audioread 讀取音頻文件並提取節奏點
def load_audio(file_path):
    y = []
    with audioread.audio_open(file_path) as input_file:
        sr = input_file.samplerate
        n_channels = input_file.channels
        for frame in input_file:
            y.extend(np.frombuffer(frame, dtype=np.int16))
        y = np.array(y, dtype=np.float32)
        y = y / (2**15)
    return y, sr

# 圓圈類
class Circle:
    def __init__(self, x, y, radius, time_to_show):
        self.x = x
        self.y = y
        self.radius = radius
        self.time_to_show = time_to_show
        self.clicked = False

    def draw(self, screen):
        if not self.clicked:
            pygame.draw.circle(screen, (255, 0, 0), (self.x, self.y), self.radius, 2)

    def click(self):
        self.clicked = True

class MusicGameApp(QWidget):
    def __init__(self):
        super().__init__()

        # 設定窗口標題和大小
        self.setWindowTitle('Music Game App')
        self.setGeometry(100, 100, 800, 600)

        # 設置窗口圖標
        self.setWindowIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\doge.jpg'))

        # 設置顏色調色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        # 創建主佈局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)

        # 頂部區域
        top_frame = QFrame()
        top_frame.setFixedHeight(60)
        top_frame.setStyleSheet("background-color: #1DB954;")
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 0, 20, 0)

        # 創建標題
        title = QLabel('LeonBot Music Player')
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: white;')
        top_layout.addWidget(title)
        top_layout.addStretch()
        top_frame.setLayout(top_layout)
        main_layout.addWidget(top_frame)

        # 中間區域
        content_frame = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)

        # 扫描指定文件夾中的音樂文件
        self.track_list_widget = QListWidget()
        self.track_list_widget.setStyleSheet("background-color: #121212; color: white; border: none;")
        self.music_folder = r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\musicdata'
        self.track_list = self.scan_music_folder()
        for track in self.track_list:
            item = QListWidgetItem(os.path.basename(track))  # 只顯示文件名
            self.track_list_widget.addItem(item)
        self.track_list_widget.itemClicked.connect(self.on_item_clicked)  # 連接列表項點擊事件
        content_layout.addWidget(self.track_list_widget)

        content_frame.setLayout(content_layout)
        main_layout.addWidget(content_frame)

        # 底部區域
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(100)
        bottom_frame.setStyleSheet("background-color: #282828;")
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(20, 10, 20, 10)

        # 播放控制按鈕
        control_layout = QHBoxLayout()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.setStyleSheet("background-color: #1DB954; border: none;")
        self.prev_button.clicked.connect(self.prev_track)
        control_layout.addWidget(self.prev_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setStyleSheet("background-color: #1DB954; border: none;")
        self.play_button.clicked.connect(self.play_pause_music)
        control_layout.addWidget(self.play_button)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.setStyleSheet("background-color: #1DB954; border: none;")
        self.next_button.clicked.connect(self.next_track)
        control_layout.addWidget(self.next_button)

        bottom_layout.addLayout(control_layout)

        # 進度條
        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Horizontal)  # 使用 Qt.Horizontal
        self.progress_slider.setStyleSheet("background-color: #404040;")
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        bottom_layout.addWidget(self.progress_slider)

        # 時間標籤
        self.time_label = QLabel('Remaining Time: 00:00')
        self.time_label.setStyleSheet('color: white;')
        bottom_layout.addWidget(self.time_label)

        bottom_frame.setLayout(bottom_layout)
        main_layout.addWidget(bottom_frame)

        # 設置主佈局
        self.setLayout(main_layout)

        # 初始化一些變數
        self.is_playing = False
        self.mode = 'listening'  # 可以是 'listening' 或 'gaming'
        self.current_track_index = 0

        # 初始化 QMediaPlayer
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.update_progress_slider)
        self.player.durationChanged.connect(self.update_duration)

        # 設置拖動條用來更新音樂位置
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)

        # 初始化Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("OSU-like Music Game")
        self.clock = pygame.time.Clock()
        self.circles = []

    def prev_track(self):
        self.current_track_index = (self.current_track_index - 1) % len(self.track_list)
        self.play_music()

    def next_track(self):
        self.current_track_index = (self.current_track_index + 1) % len(self.track_list)
        self.play_music()

    def on_item_clicked(self, item):
        # 點擊列表項目時切換到該曲目並播放
        index = self.track_list_widget.row(item)
        self.current_track_index = index
        self.play_music()

    def scan_music_folder(self):
        """扫描音樂文件夾，返回所有的mp3文件路径列表"""
        music_files = []
        for file in os.listdir(self.music_folder):
            if file.endswith('.mp3'):
                music_files.append(os.path.join(self.music_folder, file))
        return music_files

    def convert_to_wav(self, track_path):
        """將 MP3 文件轉換為 WAV 文件"""
        wav_path = track_path.replace('.mp3', '.wav')
        if os.path.exists(wav_path):
            os.remove(wav_path)
        audio = AudioSegment.from_file(track_path)
        audio.export(wav_path, format='wav')
        return wav_path

    def play_pause_music(self):
        if self.is_playing:
            self.player.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.is_playing = not self.is_playing

    def play_music(self):
        track_path = self.track_list[self.current_track_index]
        wav_path = self.convert_to_wav(track_path)
        url = QUrl.fromLocalFile(wav_path)
        self.player.setMedia(QMediaContent(url))
        self.player.play()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.is_playing = True

        # 讀取音頻文件並提取節奏點
        y, sr = load_audio(track_path)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
        beat_times = beats[::5]  # 選擇每隔五個節奏點

        # 清空圓圈列表
        self.circles.clear()

        # 生成圓圈
        for beat_time in beat_times:
            self.generate_circle(beat_time)

        # 打印生成的圓圈信息
        for circle in self.circles:
            print(f"Circle: {circle.x}, {circle.y}, {circle.radius}, {circle.time_to_show}")

        # 開始遊戲循環
        self.run_game()

    def generate_circle(self, time_to_show):
        x = random.randint(50, 750)
        y = random.randint(50, 550)
        radius = 40
        circle = Circle(x, y, radius, time_to_show)
        self.circles.append(circle)

    def run_game(self):
        running = True
        pygame.mixer.music.load(self.convert_to_wav(self.track_list[self.current_track_index]))
        pygame.mixer.music.play()
        start_time = time.time()
        while running:
            self.screen.fill((255, 255, 255))

            # 檢查事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    for circle in self.circles:
                        if not circle.clicked:
                            distance = ((circle.x - mouse_x) ** 2 + (circle.y - mouse_y) ** 2) ** 0.5
                            if distance <= circle.radius:
                                circle.click()

            # 更新並繪製圓圈
            current_time = time.time() - start_time
            for circle in self.circles:
                if circle.time_to_show <= current_time and not circle.clicked:
                    circle.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

    def update_progress_slider(self, position):
        self.progress_slider.setValue(position // 1000)
        self.update_time_label(position // 1000)

    def update_duration(self, duration):
        self.progress_slider.setMaximum(duration // 1000)

    def update_time_label(self, current_position):
        # 更新時間標籤，顯示剩餘時間
        remaining_seconds = self.progress_slider.maximum() - current_position
        remaining_time = QTime(0, (remaining_seconds // 60) % 60, remaining_seconds % 60)
        self.time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')

    def slider_pressed(self):
        # 停止播放器，避免在拖動進度條時更新衝突
        self.player.pause()

    def slider_released(self):
        # 當用戶拖動進度條時，跳轉到指定位置
        seek_seconds = self.progress_slider.value() * 1000
        self.player.setPosition(seek_seconds)
        self.player.play()

    def switch_mode(self):
        if self.mode == 'listening':
            self.mode = 'gaming'
            self.switch_mode_button.setText('Switch to Listening Mode')
            # 添加切換到遊戲模式的邏輯
        else:
            self.mode = 'listening'
            self.switch_mode_button.setText('Switch to Gaming Mode')
            # 添加切換到聽歌模式的邏輯

    def stop_music(self):
        self.player.stop()
        self.is_playing = False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    music_game_app = MusicGameApp()
    music_game_app.show()
    sys.exit(app.exec_())
