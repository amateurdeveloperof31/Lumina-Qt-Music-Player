# --------------------------------------------------- Imports ----------------------------------------------------------
from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QVBoxLayout, QGraphicsDropShadowEffect,
                               QHBoxLayout,QLabel, QPushButton, QSlider, QFileDialog, QScrollArea, QMessageBox)
from PySide6.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPainterPath
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize
from PySide6.QtSvgWidgets import QSvgWidget
import threading
import sys
from mutagen.id3 import ID3
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen import MutagenError
import json
import os
from apps.utils.musicbrainz_api import MusicBrainzAPI
import requests
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame.mixer as mixer
from pathlib import Path
# ---------------------------------------------------- Main ------------------------------------------------------------
class MusicPlayerUI(QWidget):
    def __init__(self):
        super().__init__()

        # Window Settings
        self.setWindowTitle("Lumina")
        self.width, self.height = 800, 600
        self.setFixedSize(self.width, self.height)
        self.setWindowIcon(QIcon("assets/images/window_icon.png"))

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progressbar)

        # Variables
        self.folder_path_label = "Select a Folder First!!"
        self.song_title = ""
        self.song_artist = ""
        self.song_album_art = None
        self.current_song_idx = 1
        self.previous_song_idx = None
        self.current_song_length = 0
        self.folder_path = None
        self.current_song_location = None
        self.song_time = None
        self.total_songs = 0
        self.playlist = {}
        self.playlist_items = []

        window_background = '#121212'

        # Play State: {0: Starting - Paused, 1: Loaded - Paused, 2: Play, 3: Paused}
        self.play_state = 0

        self.setStyleSheet(""" background-color: """ f'{window_background}' """; """)

        mixer.init()
        
        self.create_widgets()
# ----------------------------------------------- Create Widgets -------------------------------------------------------
    def create_widgets(self):
        # Main layout
        main_layout = QHBoxLayout(self)

        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(20)

        # Playlist Frame
        self.playlist_frame = QFrame()
        self.playlist_frame.setFixedSize(int(self.width * 0.3), int(self.height * 0.9))
        self.playlist_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 190);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 25px;
            }
        """)

        playlist_shadow = QGraphicsDropShadowEffect()

        playlist_shadow.setBlurRadius(40)
        playlist_shadow.setOffset(0, 10)
        playlist_shadow.setColor(QColor(0, 0, 0, 180))

        self.playlist_frame.setGraphicsEffect(playlist_shadow)

        playlist_layout = QVBoxLayout(self.playlist_frame)

        playlist_layout.setContentsMargins(20, 20, 20, 20)
        playlist_layout.setSpacing(15)

        select_folder_btn = QPushButton("📁 Select Folder")
        select_folder_btn.setFixedHeight(55)
        select_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,10);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 18px;
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding-left: 15px;
                padding-right: 15px;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,18);
            }

            QPushButton:pressed {
                background-color: rgba(255,255,255,25);
            }
        """)

        select_folder_btn.clicked.connect(self.select_song_folder)
        playlist_layout.addWidget(select_folder_btn)

        top_line = QFrame()
        top_line.setFrameShape(QFrame.HLine)
        top_line.setStyleSheet("""
            background-color: rgba(255,255,255,40);
            max-height: 1px;
            border: none;
        """)

        playlist_layout.addWidget(top_line)
        playlist_layout.addSpacing(10)

        # Scroll Area
        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QWidget {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                border: none;
                background: rgba(255,255,255,10);

                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical {
                background: rgba(255,255,255,40);
                min-height: 20px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,70);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar:horizontal {
                height: 0px;
            }
        """)

        # Container widget inside scroll area
        scroll_container = QWidget()
        scroll_container.setStyleSheet("""
            background: transparent;
        """)

        self.songs_layout = QVBoxLayout(scroll_container)
        self.songs_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.songs_layout.setContentsMargins(0, 0, 12, 0)
        self.songs_layout.setSpacing(12)

        self.songs_layout.addStretch()
        self.scroll_area.setWidget(scroll_container)
        playlist_layout.addWidget(self.scroll_area)

        self.footer = QLabel("P L A Y L I S T")
        self.footer.setStyleSheet("""
                            border: none;
                            background: transparent;
                            color: rgba(255,255,255,90);
                            font-size: 14px;
                            letter-spacing: 4px;
                        """)

        bottom_line = QFrame()

        bottom_line.setFrameShape(QFrame.HLine)

        bottom_line.setStyleSheet("""
            background-color: rgba(255,255,255,40);
            max-height: 1px;
            border: none;
        """)

        playlist_layout.addWidget(bottom_line)
        playlist_layout.addWidget(self.footer)

        # Media Frame
        self.media_frame = QFrame()
        self.media_frame.setFixedSize(int(self.width * 0.65), int(self.height * 0.9))
        self.media_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 190);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 25px;
            }
        """)

        media_shadow = QGraphicsDropShadowEffect()

        media_shadow.setBlurRadius(50)
        media_shadow.setOffset(0, 10)
        media_shadow.setColor(QColor(0, 0, 0, 180))

        self.media_frame.setGraphicsEffect(media_shadow)

        # Add widgets
        main_layout.addWidget(self.playlist_frame)
        main_layout.addWidget(self.media_frame)

        # Album Art
        self.bg_image = QLabel(self.media_frame)
        self.set_album_art("assets/images/default.png")
        self.bg_image.setGeometry(0, 0, self.media_frame.width(), self.media_frame.height())

        Qt.KeepAspectRatioByExpanding

        # Glass Overlay
        self.overlay = QFrame(self.media_frame)
        self.overlay.setGeometry(0, 0, self.media_frame.width(), self.media_frame.height())

        self.overlay.setStyleSheet("""
                    QFrame {
                        border-radius: 25px;

                        background: qlineargradient(
                            x1:0, y1:0,
                            x2:0, y2:1,

                            stop:0 rgba(0,0,0,10),
                            stop:0.5 rgba(0,0,0,40),
                            stop:0.7 rgba(0,0,0,90),
                            stop:1 rgba(0,0,0,210)
                        );
                    }
                """)

        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(40, 40, 40, 40)
        overlay_layout.addStretch()

        self.song_name_label = QLabel("After Dark")
        self.song_name_label.setFont(QFont("Segoe UI", 34, QFont.Bold))
        self.song_name_label.setStyleSheet("""
            border: none;
            background: transparent;
            color: white;
        """)

        self.song_artist_label = QLabel("Mr.Kitty")
        self.song_artist_label.setStyleSheet("""
                    color: rgba(255,255,255,170);
                    font-size: 20px;
                    border: none;
                    background: transparent;
                """)

        overlay_layout.addWidget(self.song_name_label)
        overlay_layout.addWidget(self.song_artist_label)

        overlay_layout.addSpacing(20)

        # ProgressBar
        progress_layout = QHBoxLayout()

        self.song_current_duration = QLabel("1:16")
        self.song_total_duration = QLabel("2:58")

        for label in [self.song_current_duration, self.song_total_duration]:
            label.setStyleSheet("""
                border: none;
                background: transparent;
                color: rgba(255,255,255,170);
                font-size: 14px;
            """)

        self.song_progress_bar = QSlider(Qt.Horizontal)
        self.song_progress_bar.setValue(0)
        self.song_progress_bar.setStyleSheet("""
            QSlider {
                background: transparent;
                border: none;
            }

            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255,255,255,30);
                border-radius: 2px;
            }

            QSlider::sub-page:horizontal {
                background: white;
                border-radius: 2px;
            }

            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                height: 14px;

                margin: -5px 0;
                border-radius: 7px;
            }
        """)

        self.song_progress_bar.sliderPressed.connect(self.progress_timer.stop)
        self.song_progress_bar.sliderReleased.connect(self.manual_slider_positioning)

        progress_layout.addWidget(self.song_current_duration)
        progress_layout.addWidget(self.song_progress_bar)
        progress_layout.addWidget(self.song_total_duration)

        overlay_layout.addLayout(progress_layout)

        overlay_layout.addSpacing(30)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)

        # Previous Button
        self.previous_button = QPushButton()
        self.previous_button.setFixedSize(55, 55)
        self.previous_button.setIcon(QIcon("assets/images/left.svg"))
        self.previous_button.setIconSize(QSize(28, 28))
        self.previous_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,8);
                border-radius: 27px;
                border: none;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,20);
            }
        """)

        self.previous_button.clicked.connect(self.previous_song)

        controls_layout.addWidget(self.previous_button)

        # Play Button
        self.play_button = QPushButton()
        self.play_button.setFixedSize(75, 75)
        self.play_button.setIcon(QIcon("assets/images/play.svg"))
        self.play_button.setIconSize(QSize(36, 36))
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,18);
                border-radius: 37px;
                border: none;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,28);
            }
        """)

        self.play_button.clicked.connect(self.play_song)

        controls_layout.addWidget(self.play_button)

        # Next Button
        self.next_button = QPushButton()
        self.next_button.setFixedSize(55, 55)
        self.next_button.setIcon(QIcon("assets/images/right.svg"))
        self.next_button.setIconSize(QSize(28, 28))
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,8);
                border-radius: 27px;
                border: none;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,20);
            }
        """)

        self.next_button.clicked.connect(self.next_song)

        controls_layout.addWidget(self.next_button)
        overlay_layout.addLayout(controls_layout)

        self.load_settings_file()
# ----------------------------------------------- Mute/Unmute Song -----------------------------------------------------
    def mute_unmute(self):
        global muted, song_volume
        if muted == 0:
            muted = 1
            mixer.music.set_volume(song_volume)
        else:
            muted = 0
            mixer.music.set_volume(0.0)
# -------------------------------------------------- Play Song ---------------------------------------------------------
    def play_song(self):
        if self.play_state == 0:
            self.play_state = 1
        elif self.play_state == 1:
            self.play_state = 2
            if self.song_time:
                mixer.music.play()
                mixer.music.rewind()
                mixer.music.set_pos(self.song_time)
            else:
                mixer.music.play()
            self.progress_timer.start(1000)
            self.play_button.setIcon(QIcon("assets/images/pause.svg"))
        elif self.play_state == 2:
            self.play_state = 3
            self.play_button.setIcon(QIcon("assets/images/play.svg"))
            self.progress_timer.stop()
            mixer.music.pause()
        else:
            self.play_state = 2
            self.play_button.setIcon(QIcon("assets/images/pause.svg"))
            mixer.music.unpause()
            self.progress_timer.start(1000)
# -------------------------------------------------- Next Song ---------------------------------------------------------
    def next_song(self):
        self.song_time = None
        if self.current_song_idx < self.total_songs:
            self.previous_song_idx = self.current_song_idx
            self.current_song_idx += 1
            self.current_song_location = self.playlist[self.current_song_idx]['song_location']
            self.load_song(True)
# ------------------------------------------------ Previous Song -------------------------------------------------------
    def previous_song(self):
        self.song_time = None
        if self.current_song_idx > 1:
            self.previous_song_idx = self.current_song_idx
            self.current_song_idx -= 1
            self.current_song_location = self.playlist[self.current_song_idx]['song_location']
            self.load_song(True)
# -------------------------------------------- Select from Playlist-----------------------------------------------------
    def on_double_click(self, label_number):
        self.previous_song_idx = self.current_song_idx
        self.current_song_idx = label_number
        self.current_song_location = self.playlist[self.current_song_idx]['song_location']
        self.song_time = None
        self.load_song(True)
# --------------------------------------------- Select Song Folder -----------------------------------------------------
    def select_song_folder(self):
        self.folder_path = QFileDialog.getExistingDirectory()

        if self.folder_path:
            self.current_song_location = None
            self.song_time = None
            self.current_song_idx = 1
            self.previous_song_idx = None
            settings = {
                "folder_path": self.folder_path,
                "current_song_location": self.current_song_location,
                "current_song_time": self.song_time
            }

            os.makedirs("misc", exist_ok=True)

            with open('misc/mmp_settings.json', 'w') as settings_file:
                settings_file.write(json.dumps(settings))

            self.load_settings_file(True)
# ------------------------------------------------ Load Settings -------------------------------------------------------
    def load_settings_file(self, autoplay=False):
        try:
            with open("misc/mmp_settings.json", "r") as settings_file:
                settings_data = settings_file.read()
        except FileNotFoundError:
            settings = {
                "folder_path": None,
                "current_song_location": None,
                "current_song_time": None
            }
            with open('misc/mmp_settings.json', 'w') as settings_file:
                settings_file.write(json.dumps(settings, indent=4))
        else:
            settings_dict = json.loads(settings_data)
            self.folder_path = settings_dict['folder_path']
            if self.folder_path and os.path.isdir(self.folder_path):
                try:
                    self.current_song_location = settings_dict['current_song_location']
                    self.song_time = settings_dict['current_song_time']
                except json.decoder.JSONDecodeError:
                    self.current_song_location = None
                    self.song_time = None
            else:
                self.current_song_location = None
                self.song_time = None

            self.load_playlist(autoplay)
# ------------------------------------------------ Load Playlist -------------------------------------------------------
    def load_playlist(self, autoplay=False):
        supported = {"MP3": MP3, "FLAC": FLAC, "WAV": WAVE}

        if not self.folder_path or not os.path.isdir(self.folder_path):
            self.folder_path_label = "Select a Folder."
            QMessageBox.warning(self, "Warning!!", "No Folder Selected! Select a Folder First")
            return

        temp_playlist = []
        self.playlist_items = []
        self.playlist = {}
        self.clear_layout(self.songs_layout)

        for song_file in Path(self.folder_path).rglob("*"):
            ext = song_file.suffix.upper().replace(".", "")
            if ext not in supported:
                continue

            fullpath = str(song_file)

            try:
                tags = supported[ext](fullpath)
                if ext == "FLAC":
                    flac_title = tags.get("TITLE")
                    song_title = str(tags.get('TITLE')[0])
                    song_artist = str(tags.get('ARTIST')[0])
                    song_album = str(tags.get('ALBUM')[0])
                    album_artist = str(tags.get('ALBUMARTIST')[0])
                    if flac_title:
                        song_title = flac_title[0]
                else:
                    id3title = tags.tags.get("TIT2") if tags.tags else None
                    song_title = str(tags.get('TIT2'))
                    song_artist = str(tags.get('TPE1'))
                    song_album = str(tags.get('TALB'))
                    album_artist = str(tags.get('TPE2'))
                    if id3title:
                        song_title = str(id3title)

            except (HeaderNotFoundError, MutagenError, KeyError, TypeError):
                print('Error reading the tags')
                continue

            if not song_title or song_title == 'None':
                song_title = song_file.stem

            album_art_image, image_location = self.get_song_thumbnail(tags, song_title, song_artist, ext)

            temp_playlist.append(
                {
                    'song_title': song_title,
                    'song_artist': song_artist,
                    'song_location': fullpath,
                    'song_ext': ext,
                    'song_length': int(tags.info.length),
                    'song_art': album_art_image,
                    'song_album': song_album,
                    'song_album_artist': album_artist
                }
            )

            self.total_songs += 1

        temp_playlist.sort(key=lambda x: x['song_title'].lower())
        self.playlist = {i + 1: item for i, item in enumerate(temp_playlist)}

        for idx, song_data in self.playlist.items():
            mins, secs = int(song_data['song_length'] / 60), int(song_data['song_length'] % 60)
            song_l = ("{:02d}:{:02d}".format(mins, secs))
            item = PlaylistItem(song_data['song_art'], song_data['song_title'], song_l, idx)
            item.double_clicked.connect(self.on_double_click)
            self.playlist_items.append(item)
            self.songs_layout.addWidget(item, alignment=Qt.AlignLeft)

        # Update Folder Name
        self.folder_path_label = os.path.basename(self.folder_path)
        shortened_folder_name = self.word_shorten(self.folder_path_label, 40)
        self.footer.setText(shortened_folder_name.upper())

        if not self.current_song_location or not self.current_song_location.strip():
            self.current_song_location = self.playlist[self.current_song_idx]['song_location']
        else:
            self.current_song_idx = next((k for k, v in self.playlist.items()
                          if Path(v['song_location']).resolve() == Path(self.current_song_location).resolve()), None)

        self.load_song(autoplay)
# -------------------------------------------------- Load Song ---------------------------------------------------------
    def load_song(self, autoplay=False):
        current_time = int(self.song_time) if self.song_time else 0
        self.progress_timer.stop()
        self.current_song_length = self.playlist[self.current_song_idx]['song_length']
        song_mins = int(self.current_song_length / 60)
        song_secs = int(self.current_song_length % 60)
        minutes, seconds = divmod(current_time,60)
        self.song_progress_bar.setMaximum(self.current_song_length)
        self.song_progress_bar.setValue(current_time)
        self.song_current_duration.setText("{:02d}:{:02d}".format(minutes, seconds))
        self.song_total_duration.setText("{:02d}:{:02d}".format(song_mins, song_secs))
        mixer.music.load(self.playlist[self.current_song_idx]['song_location'])

        if self.previous_song_idx:
            self.playlist_items[self.previous_song_idx - 1].set_active(False)
        self.playlist_items[self.current_song_idx - 1].set_active(True)
        self.scroll_area.ensureWidgetVisible(self.playlist_items[self.current_song_idx - 1], 0,
                                                                self.playlist_items[self.current_song_idx - 1].height())

        self.song_title = self.playlist[self.current_song_idx]['song_title']
        self.song_artist = self.playlist[self.current_song_idx]['song_artist']
        self.song_album_art = self.playlist[self.current_song_idx]['song_art']

        self.update_music_info()
        if not self.song_time:
            self.song_time = 0
        self.play_state = 1
        if autoplay:
            self.play_song()
        else:
            self.play_button.setIcon(QIcon("assets/images/play.svg"))
# ----------------------------------------------- Song Thumbnails ------------------------------------------------------
    def get_song_thumbnail(self, tags, song_title, song_artist, song_ext):
        sasa_joined = f"{song_title} {song_artist}"
        image_file_name = ''.join(letter for letter in sasa_joined if letter.isalnum())
        image_location = f"images/album_art/{image_file_name}.png"

        os.makedirs("images/album_art", exist_ok=True)

        if os.path.exists(image_location):
            pixmap = QPixmap(image_location)
            scaled = pixmap.scaled(450, 450, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

            return scaled, image_location

        pict = None

        try:
            if song_ext == "MP3":
                apic = tags.get("APIC:")
                if apic:
                    pict = apic.data
            elif song_ext == "FLAC":
                if tags.pictures:
                    pict = tags.pictures[0].data

            if pict:
                with open(image_location, "wb") as image_file:
                    image_file.write(pict)
        except Exception as e:
            print(f"Embedded Art Error: {e}")

        if not os.path.exists(image_location):
            threading.Thread(
                target=self.download_album_art_thread,
                args=(song_title,song_artist,image_location), daemon=True).start()

            image_location = ("assets/images/default.png")

        pixmap = QPixmap(image_location)
        scaled = pixmap.scaled(450, 450, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        return scaled, image_location
# ------------------------------------------- Download Song Thumbnails -------------------------------------------------
    def download_album_art_thread(self, song_title, song_artist, image_location):
        try:
            api = MusicBrainzAPI()
            response = api.search_releases(f'release:{song_title} 'f'AND artist:{song_artist}')
            if not response:
                return
            images = response.get("images")
            if not images:
                return
            album_art_url = (images[0].get("image"))
            if not album_art_url:
                return
            img_data = requests.get(album_art_url, timeout=3).content
            with open(image_location, "wb") as handler:
                handler.write(img_data)

        except Exception as e:

            print(
                f"Online Album Art Error: {e}"
            )
# ------------------------------------------------- Set Album Art ------------------------------------------------------
    def set_album_art(self, image_path):
        pixmap = QPixmap(image_path)
        scaled = pixmap.scaled(self.media_frame.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded = QPixmap(self.media_frame.size())

        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.media_frame.width(), self.media_frame.height(), 25, 25)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        self.bg_image.setPixmap(rounded)
# ------------------------------------------------- Music Info ---------------------------------------------------------
    def update_music_info(self):
        self.song_name_label.setText(self.song_title)
        self.song_artist_label.setText(self.song_artist)
        self.set_album_art(self.song_album_art)
# ------------------------------------------------ Progress Bar --------------------------------------------------------
    def update_progressbar(self):
        if self.play_state != 2:
            return

        temp_time = mixer.music.get_pos() / 1000
        current_time = round(temp_time + self.song_time) if self.song_time else round(temp_time)
        self.song_progress_bar.setValue(int(current_time))
        minutes, seconds = divmod(round(current_time), 60)
        self.song_current_duration.setText("{:02d}:{:02d}".format(minutes, seconds))

        if current_time >= int(self.current_song_length) - 1:
            self.progress_timer.stop()
            if self.current_song_idx < len(self.playlist):
                self.next_song()
            else:
                self.song_time = 0
                self.current_song_idx = 1
                self.previous_song_idx = None
                self.current_song_location = None
                self.play_state = 0
                mixer.music.stop()
                self.song_progress_bar.setValue(0)
                self.song_current_duration.setText("00:00")
                self.load_playlist()
# -------------------------------------------- Manual Progress Bar -----------------------------------------------------
    def manual_slider_positioning(self):
        current_time = int(self.song_progress_bar.value())
        self.song_time = current_time
        mixer.music.stop()
        mixer.music.play(start=current_time)
        minutes, seconds = divmod(int(current_time), 60)
        self.song_current_duration.setText("{:02d}:{:02d}".format(minutes, seconds))
        self.play_state = 2
        self.play_button.setIcon(QIcon("assets/images/pause.svg"))
        self.progress_timer.start(1000)
        if current_time == int(self.current_song_length) - 1:
            self.next_song()
# -------------------------------------------------- On Close ----------------------------------------------------------
    def closeEvent(self, event):
        try:
            current_song_time = (mixer.music.get_pos() / 1000)
            self.progress_timer.stop()
            if self.song_time:
                current_song_time += self.song_time
            if current_song_time < 0:
                current_song_time = 0
            current_position = {
                'current_song_location': self.current_song_location,
                'current_song_time': current_song_time
            }

            settings_path = Path("misc/mmp_settings.json")
            with settings_path.open("r+", encoding="utf-8") as f:
                settings_data = json.load(f)
                settings_data.update(current_position)
                f.seek(0)
                json.dump(settings_data, f, indent=4)
                f.truncate()

        except Exception as e:
            print(e)
            settings = {
                "folder_path": None,
                "current_song_location": None,
                "current_song_time": None
            }
            with open('misc/mmp_settings.json', 'w') as settings_file:
                settings_file.write(json.dumps(settings, indent=4))

        mixer.music.stop()
        event.accept()
# ------------------------------------------------ Shorten Word --------------------------------------------------------
    def word_shorten(self, word, limit=35):
        shortened_word = (word[:limit] + "...") if len(word) > limit else word
        return shortened_word
# ------------------------------------------------ Clear Layout --------------------------------------------------------
    def clear_layout(self, layout):
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

            child_layout = item.layout()
            if child_layout is not None:
                self.clear_layout(child_layout)

            del item
# ------------------------------------------------- Playlist Frame -----------------------------------------------------
class PlaylistItem(QFrame):
    double_clicked = Signal(int)
    def __init__(self, image, title, duration, index, active=False):
        super().__init__()

        self.active = active
        self.title = title
        self.duration = duration
        self.index = index

        self.setFixedSize(180, 70)

        layout = QHBoxLayout(self)

        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        cover = QLabel()
        image_size = 40
        pix = QPixmap(image).scaled(image_size, image_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # Rounded image
        rounded = QPixmap(image_size, image_size)
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, image_size, image_size, 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pix)
        painter.end()
        cover.setPixmap(rounded)
        cover.setFixedSize(image_size, image_size)
        cover.setStyleSheet("""
            border: none;
            background: transparent;
        """)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Song Title
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 11))

        self.title_label.setStyleSheet("""
            border: none;
            background: transparent;
            color: white;
        """)

        self.title_label.setMaximumWidth(130)

        metrics = self.title_label.fontMetrics()

        elided = metrics.elidedText(title, Qt.ElideRight, 130)

        self.title_label.setText(elided)
        self.title_label.setWordWrap(False)

        # Duration
        self.duration_label = QLabel(str(duration))
        self.duration_label.setStyleSheet("""
            border: none;
            background: transparent;
            color: rgba(255,255,255,120);
            font-size: 11px;
        """)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.duration_label)

        layout.addWidget(cover)
        layout.addLayout(text_layout)
        layout.addStretch()

        self.update_style()
# ------------------------------------------- Update Active Style ------------------------------------------------------
    def update_style(self):
        bg = ("rgba(255,255,255,15)" if self.active else "transparent")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: 18px;
            }}

            QLabel {{
                border: none;
                background: transparent;
                color: #f2e8d8;
            }}
        """)
# ------------------------------------------------ Set Active ----------------------------------------------------------
    def set_active(self, state):
        self.active = state
        self.update_style()
# ----------------------------------------------- Double Click ---------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.index)
        super().mouseDoubleClickEvent(event)
# --------------------------------------------------- Debug ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MusicPlayerUI()
    player.show()
    sys.exit(app.exec())