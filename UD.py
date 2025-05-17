import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QComboBox, QTextEdit,
    QMessageBox, QProgressBar, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from yt_dlp import YoutubeDL
from mutagen.id3 import ID3, APIC
from PIL import Image

# Constants
DEFAULT_SAVE_PATH = "."  # Current directory as default save path
STYLESHEET = """
    QWidget { background-color: #222; color: white; font-family: Arial; }
    QLineEdit, QComboBox {
        background-color: #333; border: 2px solid #444;
        border-radius: 10px; padding: 5px; font-size: 16px;
    }
    QPushButton {
        background-color: #3498db; border: none; border-radius: 10px;
        padding: 5px 10px; color: white; font-weight: bold; font-size: 16px;
    }
    QPushButton:hover { background-color: #2980b9; }
    QTextEdit {
        background-color: #333; border: 2px solid #444;
        border-radius: 10px; padding: 5px; font-size: 14px;
    }
    QProgressBar {
        border: 2px solid #444; border-radius: 10px; text-align: center;
    }
    QCheckBox {
        font-size: 16px;
    }
"""

# Language dictionary
LANGUAGES = {
    'en': {
        'title': "YouTube Downloader",
        'enter_url': "Enter YouTube URL",
        'url_placeholder': "e.g., https://www.youtube.com/watch?v=...",
        'save_dir': "Save Directory",
        'browse': "Browse",
        'next': "Next",
        'back': "Back",
        'download': "Download",
        'options': "Available Options:",
        'audio_only': "Audio only",
        'codec': "Select Output Codec:",
        'thumbnail': "Download and embed thumbnail (for audio only)",
        'input_error': "Please enter a valid URL.",
        'error': "Error",
        'extract_error': "Failed to extract video info: {}",
        'starting': "Starting download...\nFormat: {}\nCodec: {}",
        'will_thumbnail': "Will download and embed thumbnail",
        'options_for': "Options for: {}",
    },
    'uk': {
        'title': "Завантажувач YouTube",
        'enter_url': "Введіть посилання YouTube",
        'url_placeholder': "наприклад, https://www.youtube.com/watch?v=...",
        'save_dir': "Каталог збереження",
        'browse': "Огляд",
        'next': "Далі",
        'back': "Назад",
        'download': "Завантажити",
        'options': "Доступні опції:",
        'audio_only': "Тільки аудіо",
        'codec': "Виберіть кодек виходу:",
        'thumbnail': "Завантажити та вставити обкладинку (тільки для аудіо)",
        'input_error': "Будь ласка, введіть коректне посилання.",
        'error': "Помилка",
        'extract_error': "Не вдалося отримати інформацію про відео: {}",
        'starting': "Початок завантаження...\nФормат: {}\nКодек: {}",
        'will_thumbnail': "Буде завантажено та вставлено обкладинку",
        'options_for': "Опції для: {}",
    }
}

# Worker thread for downloading and embedding thumbnail
class DownloadWorker(QThread):
    progress = pyqtSignal(str)          # For log messages
    progress_update = pyqtSignal(int)   # For progress bar updates
    finished = pyqtSignal(bool, str)    # For completion status

    def __init__(self, url, save_path, selected_format, selected_codec, download_thumbnail=False):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.selected_format = selected_format
        self.selected_codec = selected_codec
        self.download_thumbnail = download_thumbnail
        self.is_video = self.selected_format != "bestaudio"
        self.download_max_progress = 90 if self.is_video else 100  # Reserve 10% for re-encoding if video
        self.files_progress = {}
        self.total_download_bytes = 0
        self.downloaded_bytes = 0
        self.downloaded_file = None

    def run(self):
        if self.is_video:
            ydl_opts = {
                'format': f"{self.selected_format}+bestaudio/best",
                'outtmpl': os.path.join(self.save_path, "%(title)s.%(ext)s"),
                'progress_hooks': [self.progress_hook],
                'merge_output_format': 'mp4',
            }
            info = self.download_with_ydl(ydl_opts)
            if info:
                if self.selected_codec != "Original":
                    self.reencode_video()
                else:
                    self.progress_update.emit(100)
                    self.finished.emit(True, "Download completed successfully!")
            else:
                self.finished.emit(False, "Download failed")
        else:
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.save_path, "%(title)s.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'progress_hooks': [self.progress_hook],
            }
            if self.download_thumbnail:
                ydl_opts['writethumbnail'] = True
            info = self.download_with_ydl(ydl_opts)
            if info:
                self.progress_update.emit(100)
                self.finished.emit(True, "Download completed successfully!")
                # Try to find the thumbnail file by base name and common extensions
                if self.download_thumbnail:
                    base, _ = os.path.splitext(self.downloaded_file)
                    for ext in [".webp", ".jpg", ".jpeg", ".png"]:
                        candidate = base + ext
                        if os.path.exists(candidate):
                            thumbnail_file = candidate
                            if thumbnail_file.endswith(".webp"):
                                thumbnail_file = self.convert_webp_to_jpg(thumbnail_file)
                            if thumbnail_file and os.path.exists(thumbnail_file):
                                self.embed_thumbnail(self.downloaded_file, thumbnail_file)
                                break
                    else:
                        self.progress.emit("Thumbnail file not found or conversion failed")
            else:
                self.finished.emit(False, "Download failed")

    def download_with_ydl(self, ydl_opts):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                self.downloaded_file = ydl.prepare_filename(info)
                # If audio extraction, update to .mp3 if needed
                if (
                    not self.is_video
                    and 'ext' in info
                    and info['ext'] != 'mp3'
                ):
                    # The postprocessor changes the extension to mp3
                    base, _ = os.path.splitext(self.downloaded_file)
                    mp3_file = base + ".mp3"
                    if os.path.exists(mp3_file):
                        self.downloaded_file = mp3_file
                # Also handle the case where info['ext'] is already 'mp3'
                elif not self.is_video and 'ext' in info and info['ext'] == 'mp3':
                    base, _ = os.path.splitext(self.downloaded_file)
                    mp3_file = base + ".mp3"
                    if os.path.exists(mp3_file):
                        self.downloaded_file = mp3_file
                return info
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            return None

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            filename = d['filename']
            if filename not in self.files_progress:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total:
                    self.files_progress[filename] = {'total': total, 'downloaded': 0}
                    self.total_download_bytes += total
            if filename in self.files_progress:
                self.files_progress[filename]['downloaded'] = d['downloaded_bytes']
                self.downloaded_bytes = sum(f['downloaded'] for f in self.files_progress.values())
                if self.total_download_bytes > 0:
                    download_progress = (self.downloaded_bytes / self.total_download_bytes) * self.download_max_progress
                    self.progress_update.emit(int(download_progress))
        elif d['status'] == 'finished':
            filename = d['filename']
            if filename in self.files_progress:
                self.files_progress[filename]['downloaded'] = self.files_progress[filename]['total']
                self.downloaded_bytes = sum(f['downloaded'] for f in self.files_progress.values())
                if self.total_download_bytes > 0:
                    download_progress = (self.downloaded_bytes / self.total_download_bytes) * self.download_max_progress
                    self.progress_update.emit(int(download_progress))

    def reencode_video(self):
        output_file = self.downloaded_file.replace('.mp4', f'_{self.selected_codec}.mp4')
        codec_map = {
            "H.264": "libx264",
            "H.265": "libx265",
            "VP9": "libvpx-vp9",
        }
        if self.selected_codec not in codec_map:
            self.finished.emit(False, "Unsupported codec selected")
            return

        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", self.downloaded_file]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
            duration = float(result.stdout.strip())
        except Exception as e:
            self.progress.emit(f"Failed to get duration: {str(e)}")
            self.finished.emit(False, "Re-encoding failed")
            return

        cmd = [
            "ffmpeg", "-i", self.downloaded_file, "-c:v", codec_map[self.selected_codec],
            "-c:a", "aac", "-y", "-progress", "pipe:1", output_file
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        current_time = 0
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("out_time="):
                time_str = line.split("=", 1)[1]
                # out_time is in format HH:MM:SS.microseconds
                try:
                    h, m, s = time_str.split(":")
                    s = float(s)
                    current_time = int(h) * 3600 + int(m) * 60 + s
                    if duration > 0:
                        reencode_progress = 90 + (current_time / duration) * 10
                        self.progress_update.emit(int(reencode_progress))
                except Exception:
                    pass
        process.wait()
        if process.returncode == 0:
            self.progress_update.emit(100)
            self.finished.emit(True, "Re-encoding completed successfully!")
            try:
                os.remove(self.downloaded_file)
                os.rename(output_file, self.downloaded_file)
            except Exception as e:
                self.progress.emit(f"Warning: Could not replace original file: {str(e)}")
        else:
            self.finished.emit(False, "Re-encoding failed")

    def embed_thumbnail(self, audio_file, thumbnail_file):
        try:
            audio = ID3(audio_file)
            with open(thumbnail_file, "rb") as img:
                mime = "image/jpeg" if thumbnail_file.lower().endswith((".jpg", ".jpeg")) else "image/png"
                audio.add(APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Cover",
                    data=img.read()
                ))
            audio.save()
            self.progress.emit("Thumbnail embedded successfully")
        except Exception as e:
            self.progress.emit(f"Failed to embed thumbnail: {str(e)}")

    def convert_webp_to_jpg(self, webp_file):
        try:
            img = Image.open(webp_file)
            jpg_file = webp_file.replace(".webp", ".jpg")
            img.convert("RGB").save(jpg_file, "JPEG")
            return jpg_file
        except Exception as e:
            self.progress.emit(f"Failed to convert thumbnail: {str(e)}")
            return None

# Input page for URL and save path
class InputPage(QWidget):
    def __init__(self, lang_dict):
        super().__init__()
        self.lang_dict = lang_dict
        self.initUI()

    def set_language(self, lang_dict):
        self.lang_dict = lang_dict
        self.title.setText(self.lang_dict['enter_url'])
        self.url_input.setPlaceholderText(self.lang_dict['url_placeholder'])
        self.path_label.setText(self.lang_dict['save_dir'])
        self.browse_button.setText(self.lang_dict['browse'])
        self.next_button.setText(self.lang_dict['next'])

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.title = QLabel(self.lang_dict['enter_url'])
        self.title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.lang_dict['url_placeholder'])
        self.url_input.setFixedHeight(40)
        layout.addWidget(self.url_input)

        self.path_label = QLabel(self.lang_dict['save_dir'])
        self.path_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.path_label)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setFixedHeight(40)
        self.path_input.setText(DEFAULT_SAVE_PATH)
        path_layout.addWidget(self.path_input)

        self.browse_button = QPushButton(self.lang_dict['browse'])
        self.browse_button.setFixedHeight(40)
        self.browse_button.setFixedWidth(100)
        self.browse_button.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.browse_button)

        layout.addLayout(path_layout)

        self.next_button = QPushButton(self.lang_dict['next'])
        self.next_button.setFixedSize(120, 40)
        layout.addWidget(self.next_button, alignment=Qt.AlignCenter)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, self.lang_dict['browse'], self.path_input.text() or DEFAULT_SAVE_PATH)
        if directory:
            self.path_input.setText(directory)

# Options page with format and codec selection, and thumbnail checkbox
class OptionsPage(QWidget):
    def __init__(self, lang_dict):
        super().__init__()
        self.lang_dict = lang_dict
        self.initUI()

    def set_language(self, lang_dict):
        self.lang_dict = lang_dict
        self.info_label.setText(self.lang_dict['options'])
        self.thumbnail_checkbox.setText(self.lang_dict['thumbnail'])
        self.codec_label.setText(self.lang_dict['codec'])
        self.back_button.setText(self.lang_dict['back'])
        self.download_button.setText(self.lang_dict['download'])
        # Update audio only text in format_box if present
        idx = self.format_box.findData("bestaudio")
        if idx != -1:
            self.format_box.setItemText(idx, self.lang_dict['audio_only'])

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.info_label = QLabel(self.lang_dict['options'])
        self.info_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.info_label)

        self.format_box = QComboBox()
        self.format_box.setFixedHeight(40)
        self.format_box.setMinimumWidth(300)
        layout.addWidget(self.format_box)

        self.thumbnail_checkbox = QCheckBox(self.lang_dict['thumbnail'], self)
        self.thumbnail_checkbox.setEnabled(False)
        layout.addWidget(self.thumbnail_checkbox)

        self.codec_label = QLabel(self.lang_dict['codec'])
        self.codec_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.codec_label)

        self.codec_box = QComboBox()
        self.codec_box.setFixedHeight(40)
        self.codec_box.addItems(["Original", "H.264", "H.265", "VP9"])
        layout.addWidget(self.codec_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(120)
        layout.addWidget(self.log_output)

        btn_layout = QHBoxLayout()
        self.back_button = QPushButton(self.lang_dict['back'])
        self.back_button.setFixedSize(120, 40)
        btn_layout.addWidget(self.back_button)

        self.download_button = QPushButton(self.lang_dict['download'])
        self.download_button.setFixedSize(120, 40)
        btn_layout.addWidget(self.download_button)

        layout.addLayout(btn_layout)

        self.format_box.currentIndexChanged.connect(self.update_thumbnail_checkbox)

    def update_thumbnail_checkbox(self):
        if self.format_box.currentData() == "bestaudio":
            self.thumbnail_checkbox.setEnabled(True)
        else:
            self.thumbnail_checkbox.setEnabled(False)

# Main application window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_lang = 'en'
        self.lang_dict = LANGUAGES[self.current_lang]
        self.setWindowTitle(self.lang_dict['title'])
        self.resize(500, 400)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Language / Мова:")
        self.lang_box = QComboBox()
        self.lang_box.addItem("English", "en")
        self.lang_box.addItem("Українська", "uk")
        self.lang_box.setFixedWidth(120)
        self.lang_box.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_box)
        lang_layout.addStretch()
        main_layout.addLayout(lang_layout)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        self.input_page = InputPage(self.lang_dict)
        self.options_page = OptionsPage(self.lang_dict)

        self.stacked_widget.addWidget(self.input_page)
        self.stacked_widget.addWidget(self.options_page)
        self.stacked_widget.setCurrentWidget(self.input_page)

        self.input_page.next_button.clicked.connect(self.processURL)
        self.options_page.back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.input_page))
        self.options_page.download_button.clicked.connect(self.startDownload)

    def change_language(self):
        lang_code = self.lang_box.currentData()
        self.current_lang = lang_code
        self.lang_dict = LANGUAGES[lang_code]
        self.setWindowTitle(self.lang_dict['title'])
        self.input_page.set_language(self.lang_dict)
        self.options_page.set_language(self.lang_dict)

    def processURL(self):
        url = self.input_page.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, self.lang_dict['error'], self.lang_dict['input_error'])
            return
        self.save_path = self.input_page.path_input.text().strip() or DEFAULT_SAVE_PATH
        self.extract_video_info(url)

    def extract_video_info(self, url):
        try:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            self.populate_options(info)
        except Exception as e:
            QMessageBox.critical(self, self.lang_dict['error'], self.lang_dict['extract_error'].format(str(e)))

    def populate_options(self, info):
        self.options_page.format_box.clear()
        video_formats = [fmt for fmt in info['formats'] if fmt.get('vcodec') != 'none' and fmt.get('height')]
        for fmt in video_formats:
            height = fmt.get('height', 'unknown')
            vcodec = fmt.get('vcodec', 'unknown').split('.')[0]
            ext = fmt.get('ext', 'unknown')
            format_id = fmt['format_id']
            text = f"{height}p {vcodec} ({ext})"
            self.options_page.format_box.addItem(text, format_id)
        self.options_page.format_box.addItem(self.lang_dict['audio_only'], "bestaudio")
        self.options_page.log_output.clear()
        self.options_page.info_label.setText(self.lang_dict['options_for'].format(info.get('title', 'Video')))
        self.stacked_widget.setCurrentWidget(self.options_page)
        self.options_page.update_thumbnail_checkbox()

    def startDownload(self):
        url = self.input_page.url_input.text().strip()
        selected_format = self.options_page.format_box.currentData()
        selected_codec = self.options_page.codec_box.currentText()
        download_thumbnail = self.options_page.thumbnail_checkbox.isChecked() if selected_format == "bestaudio" else False
        self.options_page.log_output.append(self.lang_dict['starting'].format(self.options_page.format_box.currentText(), selected_codec))
        if download_thumbnail:
            self.options_page.log_output.append(self.lang_dict['will_thumbnail'])
        self.options_page.download_button.setEnabled(False)
        self.worker = DownloadWorker(url, self.save_path, selected_format, selected_codec, download_thumbnail)
        self.worker.progress.connect(self.options_page.log_output.append)
        self.worker.progress_update.connect(self.options_page.progress_bar.setValue)
        self.worker.finished.connect(self.downloadFinished)
        self.worker.start()

    def downloadFinished(self, success, msg):
        self.options_page.log_output.append(msg)
        self.options_page.download_button.setEnabled(True)
        self.options_page.progress_bar.setValue(0 if not success else 100)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())
