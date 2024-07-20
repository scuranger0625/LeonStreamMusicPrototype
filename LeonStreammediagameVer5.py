import sys
import os
import random
import time
import numpy as np
import audioread
import librosa
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QSlider, QStyle, QFrame, QDialog, QProgressBar
from PyQt5.QtGui import QIcon, QPalette, QColor, QPainter, QImage, QPixmap
from PyQt5.QtCore import Qt, QTime, QUrl, QTimer, pyqtSignal, QThread, QObject, QEvent
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

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super(LoadingDialog, self).__init__(parent)
        self.setWindowTitle('Loading')
        self.setGeometry(500, 300, 300, 100)
        layout = QVBoxLayout()
        self.label = QLabel("Loading, please wait...")
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def set_progress(self, value):
        self.progress_bar.setValue(value)

class PygameWidget(QWidget):
    def __init__(self, parent=None):
        super(PygameWidget, self).__init__(parent)
        self.setFixedSize(800, 600)
        self.screen = pygame.Surface((800, 600))

    def paintEvent(self, event):
        painter = QPainter(self)
        image = pygame.image.tostring(self.screen, 'RGBA')
        qimage = QImage(image, self.screen.get_width(), self.screen.get_height(), QImage.Format_RGBA8888)
        painter.drawImage(0, 0, qimage)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (pos.x(), pos.y()), 'button': 1}))

class MusicGameApp(QWidget):
    def __init__(self):
        super().__init__()

        # 設定窗口標題和大小
        self.setWindowTitle('Music Game App')
        self.setGeometry(100, 100, 1200, 600)

        # 設置窗口圖標
        self.setWindowIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\doge.jpg'))

        # 設置顏色調色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        # 創建主佈局
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(0)

        # 左側區域（音樂播放器）
        self.left_frame = QFrame()
        self.left_frame.setFixedWidth(400)
        self.left_frame.setStyleSheet("background-color: #282828;")
        self.left_layout = QVBoxLayout()
        self.left_layout.setContentsMargins(20, 20, 20, 20)

        # 創建標題
        title = QLabel('LeonBot Music Player')
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: white;')
        self.left_layout.addWidget(title)

        # 扫描指定文件夾中的音樂文件
        self.track_list_widget = QListWidget()
        self.track_list_widget.setStyleSheet("background-color: #121212; color: white; border: none;")
        self.music_folder = r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\musicdata'
        self.track_list = self.scan_music_folder()
        for track in self.track_list:
            item = QListWidgetItem(os.path.basename(track))  # 只顯示文件名
            self.track_list_widget.addItem(item)
        self.track_list_widget.itemClicked.connect(self.on_item_clicked)  # 連接列表項點擊事件
        self.left_layout.addWidget(self.track_list_widget)

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

        self.left_layout.addLayout(control_layout)

        # 進度條
        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Horizontal)  # 使用 Qt.Horizontal
        self.progress_slider.setStyleSheet("background-color: #404040;")
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.left_layout.addWidget(self.progress_slider)

        # 時間標籤
        self.time_label = QLabel('Remaining Time: 00:00')
        self.time_label.setStyleSheet('color: white;')
        self.left_layout.addWidget(self.time_label)

        # 模式切換按鈕
        self.switch_mode_button = QPushButton("Switch to Gaming Mode")
        self.switch_mode_button.setStyleSheet("background-color: #1DB954; border: none;")
        self.switch_mode_button.clicked.connect(self.switch_mode)
        self.left_layout.addWidget(self.switch_mode_button)

        self.left_frame.setLayout(self.left_layout)
        self.main_layout.addWidget(self.left_frame)

        # 右側區域（Pygame顯示）
        self.pygame_widget = PygameWidget(self)
        self.main_layout.addWidget(self.pygame_widget)

        # 設置主佈局
        self.setLayout(self.main_layout)

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

        # 創建計時器以定期更新Pygame顯示
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pygame)

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
        if self.mode == 'gaming':
            self.loading_dialog = LoadingDialog(self)
            self.loading_dialog.show()

            self.loading_thread = QThread()
            self.loading_worker = LoadingWorker(track_path)
            self.loading_worker.moveToThread(self.loading_thread)
            self.loading_worker.progress.connect(self.loading_dialog.set_progress)
            self.loading_worker.finished.connect(self.on_loading_finished)
            self.loading_thread.started.connect(self.loading_worker.process)
            self.loading_thread.start()
        else:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(track_path)))
            self.player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.is_playing = True

    def on_loading_finished(self, data):
        y, sr, tempo, beats, wav_path = data
        self.beat_times = beats[::5]

        print(f"Tempo: {tempo}")
        print(f"Selected beat times: {self.beat_times}")

        self.circles = []
        for beat_time in self.beat_times:
            self.generate_circle(beat_time)

        for circle in self.circles:
            print(f"Circle: {circle.x}, {circle.y}, {circle.radius}, {circle.time_to_show}")

        self.loading_dialog.close()
        self.run_game(wav_path)

    def generate_circle(self, time_to_show):
        x = random.randint(50, 750)
        y = random.randint(50, 550)
        radius = 40
        circle = Circle(x, y, radius, time_to_show)
        self.circles.append(circle)

    def run_game(self, wav_path):
        self.running = True
        pygame.mixer.music.load(wav_path)
        pygame.mixer.music.play()
        self.start_time = time.time()
        self.timer.start(16)  # 每16毫秒更新一次Pygame顯示

    def update_pygame(self):
        if hasattr(self, 'running') and self.running and self.mode == 'gaming':
            self.pygame_widget.screen.fill((255, 255, 255))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    for circle in self.circles:
                        if not circle.clicked:
                            distance = ((circle.x - mouse_x) ** 2 + (circle.y - mouse_y) ** 2) ** 0.5
                            if distance <= circle.radius:
                                circle.click()

            current_time = time.time() - self.start_time
            for circle in self.circles:
                if circle.time_to_show <= current_time and not circle.clicked:
                    circle.draw(self.pygame_widget.screen)

            self.pygame_widget.update()

    def update_progress_slider(self, position):
        self.progress_slider.setValue(position // 1000)
        self.update_time_label(position // 1000)

    def update_duration(self, duration):
        self.progress_slider.setMaximum(duration // 1000)

    def update_time_label(self, current_position):
        remaining_seconds = self.progress_slider.maximum() - current_position
        remaining_time = QTime(0, (remaining_seconds // 60) % 60, remaining_seconds % 60)
        self.time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')

    def slider_pressed(self):
        self.player.pause()

    def slider_released(self):
        seek_seconds = self.progress_slider.value() * 1000
        self.player.setPosition(seek_seconds)
        self.player.play()

    def switch_mode(self):
        if self.mode == 'listening':
            self.mode = 'gaming'
            self.switch_mode_button.setText('Switch to Listening Mode')
            self.play_music()
        else:
            self.mode = 'listening'
            self.switch_mode_button.setText('Switch to Gaming Mode')
            self.running = False
            self.pygame_widget.screen.fill((255, 255, 255))
            self.pygame_widget.update()
            self.play_music()

    def stop_music(self):
        self.player.stop()
        self.is_playing = False

class LoadingWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)

    def __init__(self, track_path):
        super().__init__()
        self.track_path = track_path

    def process(self):
        y, sr = load_audio(self.track_path)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
        wav_path = self.track_path.replace('.mp3', '.wav')
        audio = AudioSegment.from_file(self.track_path)
        audio.export(wav_path, format='wav')
        self.progress.emit(100)
        self.finished.emit((y, sr, tempo, beats, wav_path))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    music_game_app = MusicGameApp()
    music_game_app.show()
    sys.exit(app.exec_())
