import sys
import os
import random
import time
import numpy as np
import audioread
import librosa
import pygame
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QSlider, QStyle, QFrame, QDialog, QProgressBar
from PyQt5.QtGui import QIcon, QPalette, QColor, QPainter, QImage
from PyQt5.QtCore import Qt, QTime, QTimer, pyqtSignal, QThread, QObject
from pydub import AudioSegment
from scipy.signal import butter, lfilter

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
    def __init__(self, x, y, radius, time_to_show, letter):
        self.x = x
        self.y = y
        self.radius = radius
        self.time_to_show = time_to_show
        self.letter = letter
        self.clicked = False

    def draw(self, screen):
        if not self.clicked:
            pygame.draw.circle(screen, (255, 0, 0), (self.x, self.y), self.radius, 2)
            font = pygame.font.Font(None, 36)
            text = font.render(self.letter, True, (255, 0, 0))
            screen.blit(text, (self.x - self.radius // 2, self.y - self.radius // 2))

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

class EqualizerWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.main_layout = QVBoxLayout()
        self.slider_layout = QHBoxLayout()
        
        self.sliders = []
        self.labels = []
        self.gains = [0] * 9
        frequencies = [75, 150, 300, 600, 1200, 2400, 4800, 9600, 19200]
        for i, freq in enumerate(frequencies):
            vbox = QVBoxLayout()
            slider = QSlider(Qt.Vertical)
            slider.setRange(-10, 10)
            slider.setValue(0)
            slider.valueChanged.connect(self.update_gains)
            label = QLabel(f'{freq} Hz')
            self.sliders.append(slider)
            self.labels.append(label)
            vbox.addWidget(slider)
            vbox.addWidget(label)
            self.slider_layout.addLayout(vbox)
        
        self.main_layout.addLayout(self.slider_layout)
        
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas)
        
        self.setLayout(self.main_layout)
        
        self.update_plot()
    
    def update_gains(self):
        self.gains = [slider.value() for slider in self.sliders]
        self.update_plot()
    
    def update_plot(self):
        self.ax.clear()
        
        freqs = [75, 150, 300, 600, 1.2e3, 2.4e3, 4.8e3, 9.6e3, 19e3]
        gains = self.gains
        
        self.ax.plot(freqs, gains, marker='o', color='purple')
        self.ax.set_xscale('log')
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Gain (dB)')
        self.ax.set_title('Equalizer')
        self.ax.grid(True)
        
        self.canvas.draw()

class MusicGameApp(QWidget):
    def __init__(self):
        super().__init__()

        # 設定窗口標題和大小
        self.setWindowTitle('Music Game App')
        self.setGeometry(100, 100, 1200, 800)

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

        # 隨機播放按鈕
        self.random_play_button = QPushButton("Random Play")
        self.random_play_button.setStyleSheet("background-color: #1DB954; border: none;")
        self.random_play_button.clicked.connect(self.toggle_random_play)
        self.left_layout.addWidget(self.random_play_button)

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

        # 添加剩余时间标签和进度条到右侧区域
        self.remaining_time_label = QLabel('Remaining Time: 00:00', self)
        self.remaining_time_label.setStyleSheet('font-size: 18px; color: white;')
        self.remaining_time_bar = QProgressBar(self)
        self.remaining_time_bar.setTextVisible(False)
        self.remaining_time_bar.setStyleSheet("QProgressBar {border: 2px solid grey; border-radius: 5px; text-align: center; } QProgressBar::chunk {background-color: #05B8CC; width: 20px;}")
        
        # 添加显示圆圈数和combo数的标签
        self.circle_count_label = QLabel('Circles: 0', self)
        self.circle_count_label.setStyleSheet('font-size: 18px; color: white;')
        self.combo_count_label = QLabel('Combo: 0', self)
        self.combo_count_label.setStyleSheet('font-size: 18px; color: white;')
        self.max_combo_label = QLabel('Max Combo: 0', self)
        self.max_combo_label.setStyleSheet('font-size: 18px; color: white;')

        # 增加等化器
        self.equalizer = EqualizerWidget()

        # 设置右侧布局
        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.pygame_widget)
        self.right_layout.addWidget(self.remaining_time_label)
        self.right_layout.addWidget(self.remaining_time_bar)
        self.right_layout.addWidget(self.circle_count_label)
        self.right_layout.addWidget(self.combo_count_label)
        self.right_layout.addWidget(self.max_combo_label)
        self.right_layout.addWidget(self.equalizer)
        self.right_layout.setAlignment(Qt.AlignTop)
        self.right_frame = QFrame()
        self.right_frame.setLayout(self.right_layout)
        self.main_layout.addWidget(self.right_frame)

        # 設置主佈局
        self.setLayout(self.main_layout)

        # 初始化一些變數
        self.is_playing = False
        self.mode = 'listening'  # 可以是 'listening' 或 'gaming'
        self.current_track_index = 0
        self.combo = 0
        self.max_combo = 0
        self.random_play = False
        self.start_time = time.time()

        # 初始化Pygame
        pygame.init()

        # 創建計時器以定期更新Pygame顯示
        self.timer = QTimer(self)

        # 設置拖動條用來更新音樂位置
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)

        # 初始化播放
        pygame.mixer.init()

        # 創建計時器以定期更新進度條和時間標籤
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(1000)

        # 設置音樂結束事件
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        self.timer.timeout.connect(self.check_music_end)

    def prev_track(self):
        self.current_track_index = (self.current_track_index - 1) % len(self.track_list)
        self.play_music()

    def next_track(self):
        self.current_track_index = (self.current_track_index + 1) % len(self.track_list)
        self.play_music()

    def on_item_clicked(self, item):
        # 點擊列表項目時切換到該曲目並播放
        self.current_track_index = self.track_list_widget.row(item)
        self.play_music()

    def scan_music_folder(self):
        music_files = []
        for file in os.listdir(self.music_folder):
            if file.endswith('.mp3'):
                music_files.append(os.path.join(self.music_folder, file))
        return music_files

    def convert_to_wav(self, track_path):
        """將 MP3 文件轉換為 WAV 文件"""
        unique_suffix = f"_{random.randint(1000, 9999)}"
        wav_path = track_path.replace('.mp3', unique_suffix + '.wav')
        if os.path.exists(wav_path):
            os.remove(wav_path)
            time.sleep(0.1)  # 添加短暫等待時間，確保文件資源已被釋放
        audio = AudioSegment.from_file(track_path)
        audio.export(wav_path, format='wav')
        return wav_path

    def play_pause_music(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            pygame.mixer.music.unpause()
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
            self.loading_worker.finished.connect(self.loading_thread.quit)  # Ensure thread quits properly
            self.loading_worker.finished.connect(self.loading_worker.deleteLater)
            self.loading_thread.finished.connect(self.loading_thread.deleteLater)
            self.loading_thread.start()
        else:
            wav_path = self.convert_to_wav(track_path)
            pygame.mixer.music.load(wav_path)
            pygame.mixer.music.play()
            self.set_track_duration(wav_path)  # 設置進度條的最大值
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.is_playing = True

    def set_track_duration(self, wav_path):
        # 使用 pygame.mixer.Sound 來獲取音樂文件的長度
        sound = pygame.mixer.Sound(wav_path)
        duration = sound.get_length()
        self.progress_slider.setMaximum(int(duration))
        self.progress_slider.setValue(0)
        self.update_time_label(0)
        self.remaining_time_bar.setMaximum(int(duration))

    def update_progress(self):
        if self.is_playing:
            position = pygame.mixer.music.get_pos() // 1000
            self.progress_slider.setValue(position)
            self.update_time_label(position)
            total_length = self.progress_slider.maximum()
            remaining_seconds = total_length - position
            if remaining_seconds < 0:
                remaining_seconds = 0
            remaining_time = QTime(0, (remaining_seconds // 60) % 60, int(remaining_seconds % 60))
            self.time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')
            self.remaining_time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')
            self.remaining_time_bar.setValue(position)

    def on_loading_finished(self, data):
        y, sr, tempo, beats, wav_path = data
        self.y = y
        self.sr = sr
        self.filtered_y = y  # 初始化为原始音频数据
        self.beat_times = beats[::5]

        print(f"Tempo: {tempo}")
        print(f"Selected beat times: {self.beat_times}")

        self.circles = []
        letters = ['W', 'A', 'S', 'D']
        for beat_time in self.beat_times:
            self.generate_circle(beat_time, random.choice(letters))

        for circle in self.circles:
            print(f"Circle: {circle.x}, {circle.y}, {circle.radius}, {circle.time_to_show}, {circle.letter}")

        self.loading_dialog.close()
        self.open_game_window(wav_path, self.circles)

    def generate_circle(self, time_to_show, letter):
        x = random.randint(50, 750)
        y = random.randint(50, 550)
        radius = 40
        circle = Circle(x, y, radius, time_to_show, letter)
        self.circles.append(circle)
        self.circle_count_label.setText(f'Circles: {len(self.circles)}')

    def open_game_window(self, wav_path, circles):
        self.game_window = GameWindow(wav_path, circles, self.combo, self.max_combo)
        self.game_window.show()

    def update_time_label(self, current_position):
        remaining_seconds = self.progress_slider.maximum() - current_position
        remaining_time = QTime(0, (remaining_seconds // 60) % 60, int(remaining_seconds % 60))
        self.time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')
    
    def apply_equalizer(self, y, freqs, gains, sr):
        for freq, gain in zip(freqs, gains):
            if gain != 0:
                low = freq / np.sqrt(2)
                high = freq * np.sqrt(2)
                b, a = butter(2, [low / (0.5 * sr), high / (0.5 * sr)], btype='band')
                y = lfilter(b, a, y) * (10 ** (gain / 20))
        return y

    def update_equalizer(self):
        freqs = [75, 150, 300, 600, 1.2e3, 2.4e3, 4.8e3, 9.6e3, 19e3]
        gains = self.equalizer.gains
        self.filtered_y = self.apply_equalizer(self.y, freqs, gains, self.sr)
        temp_wav_path = "temp_filtered.wav"
        librosa.output.write_wav(temp_wav_path, self.filtered_y, self.sr)
        pygame.mixer.music.load(temp_wav_path)
        pygame.mixer.music.play()

    def slider_pressed(self):
        pygame.mixer.music.pause()

    def slider_released(self):
        seek_seconds = self.progress_slider.value()
        pygame.mixer.music.play(start=seek_seconds)
        self.is_playing = True

    def switch_mode(self):
        self.stop_music()
        if self.mode == 'listening':
            self.mode = 'gaming'
            self.switch_mode_button.setText('Switch to Listening Mode')
            self.loading_dialog = LoadingDialog(self)
            self.loading_dialog.show()
            
            self.loading_thread = QThread()
            self.loading_worker = LoadingWorker(self.track_list[self.current_track_index])
            self.loading_worker.moveToThread(self.loading_thread)
            self.loading_worker.progress.connect(self.loading_dialog.set_progress)
            self.loading_worker.finished.connect(self.on_loading_finished)
            self.loading_thread.started.connect(self.loading_worker.process)
            self.loading_worker.finished.connect(self.loading_thread.quit)  # Ensure thread quits properly
            self.loading_worker.finished.connect(self.loading_worker.deleteLater)
            self.loading_thread.finished.connect(self.loading_thread.deleteLater)
            self.loading_thread.start()
        else:
            self.mode = 'listening'
            self.switch_mode_button.setText('Switch to Gaming Mode')
            self.play_music()

    def stop_music(self):
        pygame.mixer.music.stop()
        self.is_playing = False

    def toggle_random_play(self):
        self.random_play = not self.random_play
        if self.random_play:
            self.random_play_button.setStyleSheet("background-color: #FF5733; border: none;")
        else:
            self.random_play_button.setStyleSheet("background-color: #1DB954; border: none;")

    def check_music_end(self):
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT + 1:
                if self.random_play:
                    self.current_track_index = random.randint(0, len(self.track_list) - 1)
                    self.play_music()
                else:
                    self.next_track()

    def closeEvent(self, event):
        total_use_time = time.time() - self.start_time
        print(f"Total use time: {total_use_time // 60} minutes {int(total_use_time % 60)} seconds")
        super().closeEvent(event)

class LoadingWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)

    def __init__(self, track_path):
        super().__init__()
        self.track_path = track_path

    def process(self):
        y, sr = load_audio(self.track_path)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
        unique_suffix = f"_{random.randint(1000, 9999)}"
        wav_path = self.track_path.replace('.mp3', unique_suffix + '.wav')
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            audio = AudioSegment.from_file(self.track_path)
            audio.export(wav_path, format='wav')
        except PermissionError:
            print(f"Permission denied: '{wav_path}'")
        self.progress.emit(100)
        self.finished.emit((y, sr, tempo, beats, wav_path))

class GameWindow(QMainWindow):
    def __init__(self, wav_path, circles, combo, max_combo):
        super().__init__()
        self.setWindowTitle('Game Mode')
        self.setGeometry(100, 100, 800, 600)

        self.wav_path = wav_path
        self.circles = circles
        self.combo = combo
        self.max_combo = max_combo

        self.pygame_widget = PygameWidget(self)
        self.setCentralWidget(self.pygame_widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pygame)
        self.timer.start(16)  # 每16毫秒更新一次Pygame顯示

        self.start_game()

    def start_game(self):
        self.running = True
        pygame.mixer.music.load(self.wav_path)
        pygame.mixer.music.play()
        self.start_time = time.time()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D]:
            key_letter = chr(event.key())
            self.check_circle_click(key_letter)

    def check_circle_click(self, letter):
        hit_circle = False
        for circle in self.circles:
            if not circle.clicked and circle.letter == letter:
                circle.click()
                hit_circle = True
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                break
        if not hit_circle:
            self.combo = 0

    def update_pygame(self):
        if hasattr(self, 'running') and self.running:
            self.pygame_widget.screen.fill((255, 255, 255))

            current_time = time.time() - self.start_time
            for circle in self.circles:
                if circle.time_to_show <= current_time and not circle.clicked:
                    circle.draw(self.pygame_widget.screen)

            self.pygame_widget.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    music_game_app = MusicGameApp()
    music_game_app.show()
    sys.exit(app.exec_())
