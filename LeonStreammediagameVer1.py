import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QSlider
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer, QTime
from pydub import AudioSegment
import pygame
import tempfile

class MusicGameApp(QWidget):
    def __init__(self):
        super().__init__()

        # 初始化 Pygame
        pygame.init()

        # 設定窗口標題和大小
        self.setWindowTitle('Music Game App')
        self.setGeometry(100, 100, 600, 400)

        # 設置窗口圖標
        self.setWindowIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\doge.jpg'))

        # 創建主佈局
        main_layout = QVBoxLayout()

        # 創建標題
        title = QLabel('LeonBot Music Player')
        title.setStyleSheet('font-size: 24px; font-weight: bold;')
        main_layout.addWidget(title)

        # 扫描指定文件夾中的音樂文件
        self.track_list_widget = QListWidget()
        self.music_folder = r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\musicdata'
        self.track_list = self.scan_music_folder()
        for track in self.track_list:
            item = QListWidgetItem(os.path.basename(track))  # 只顯示文件名
            self.track_list_widget.addItem(item)
        self.track_list_widget.itemClicked.connect(self.on_item_clicked)  # 連接列表項點擊事件
        main_layout.addWidget(self.track_list_widget)

        # 創建播放控制按鈕和進度條
        control_layout = QHBoxLayout()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\上一首icon.jpg'))
        self.prev_button.clicked.connect(self.prev_track)
        control_layout.addWidget(self.prev_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\playicon.jpg'))
        self.play_button.clicked.connect(self.play_pause_music)
        control_layout.addWidget(self.play_button)

        self.next_button = QPushButton()
        self.next_button.setIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\下一首 icon.jpg'))
        self.next_button.clicked.connect(self.next_track)
        control_layout.addWidget(self.next_button)

        main_layout.addLayout(control_layout)

        # 創建進度條
        self.progress_slider = QSlider()
        self.progress_slider.setOrientation(Qt.Horizontal)  # 使用 Qt.Horizontal
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        main_layout.addWidget(self.progress_slider)

        # 創建時間標籤
        self.time_label = QLabel('Remaining Time: 00:00')
        main_layout.addWidget(self.time_label)

        # 創建模式切換按鈕
        self.switch_mode_button = QPushButton('Switch to Gaming Mode')
        self.switch_mode_button.clicked.connect(self.switch_mode)
        main_layout.addWidget(self.switch_mode_button)

        # 設置主佈局
        self.setLayout(main_layout)

        # 初始化一些變數
        self.is_playing = False
        self.mode = 'listening'  # 可以是 'listening' 或 'gaming'
        self.current_track_index = 0

        # 用於暫存當前播放的音樂檔案的路徑
        self.temp_wav_path = None

        # 初始化 QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress_slider)

        # 設置拖動條用來更新音樂位置
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)

        # 用於跟踪是否正在拖動進度條
        self.dragging_slider = False

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

    def play_pause_music(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.setIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\playicon.jpg'))
        else:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.unpause()
            else:
                self.play_music()
            self.play_button.setIcon(QIcon(r'C:\Users\Leon\Desktop\python\串流音樂手機遊戲\icon\pauseicon.jpg'))
        self.is_playing = not self.is_playing

    def play_music(self):
        # 停止當前正在播放的音樂
        pygame.mixer.music.stop()

        # 播放新的音樂
        track_path = self.track_list[self.current_track_index]
        audio = AudioSegment.from_file(track_path)

        # 生成一個臨時的wav檔案
        if self.temp_wav_path:
            try:
                os.remove(self.temp_wav_path)
            except PermissionError:
                print(f"Failed to remove {self.temp_wav_path} because it's in use.")
        self.temp_wav_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        audio.export(self.temp_wav_path, format='wav')

        # 載入並播放音樂
        pygame.mixer.music.load(self.temp_wav_path)
        pygame.mixer.music.play()

        # 設置進度條最大值為音樂長度（秒）
        duration_seconds = len(audio) / 1000
        self.progress_slider.setMaximum(int(duration_seconds))

        # 啟動定時器，每1000毫秒（即1秒）更新一次進度條和時間標籤
        self.timer.start(1000)

    def update_progress_slider(self):
        # 更新進度條的值，設置為當前音樂的播放進度（秒）
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy() and not self.dragging_slider:
            current_position = pygame.mixer.music.get_pos() / 1000  # 毫秒轉換為秒
            self.progress_slider.setValue(int(current_position))
            self.update_time_label(int(current_position))
        elif not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
            self.timer.stop()


    def update_time_label(self, current_position):
        # 更新時間標籤，顯示剩餘時間
        remaining_seconds = self.progress_slider.maximum() - current_position
        remaining_time = QTime(0, (remaining_seconds // 60) % 60, remaining_seconds % 60)
        self.time_label.setText(f'Remaining Time: {remaining_time.toString("mm:ss")}')

    def slider_pressed(self):
        # 停止定時器，避免在拖動進度條時更新衝突
        self.timer.stop()
        self.dragging_slider = True

    def slider_released(self):
        # 當用戶拖動進度條時，跳轉到指定位置
        seek_seconds = self.progress_slider.value()
        
        # 檢查是否拖曳到最後
        if seek_seconds >= self.progress_slider.maximum():
            self.current_track_index = 0  # 回到第一首歌曲
            self.play_music()
        else:
            pygame.mixer.music.play(start=seek_seconds)

        # 重新啟動定時器
        self.timer.start(1000)
        self.dragging_slider = False


    def switch_mode(self):
        if self.mode == 'listening':
            self.mode = 'gaming'
            self.switch_mode_button.setText('Switch to Listening Mode')
            # 添加切換到遊戲模式的邏輯
        else:
            self.mode = 'listening'
            self.switch_mode_button.setText('Switch to Gaming Mode')
            # 添加切換到聽歌模式的邏輯
    
        def on_item_clicked(self, item):
        # 點擊列表項目時切換到該曲目並播放
            index = self.track_list_widget.row(item)
            self.current_track_index = index
            self.stop_music()  # 停止上一首音樂
            self.play_music()  # 播放新的音樂

    def stop_music(self):
        pygame.mixer.music.stop()
        if self.temp_wav_path:
            try:
                os.remove(self.temp_wav_path)
            except Exception as e:
                print(f"Failed to remove {self.temp_wav_path}: {e}")
        self.timer.stop()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    music_game_app = MusicGameApp()
    music_game_app.show()
    sys.exit(app.exec_())
