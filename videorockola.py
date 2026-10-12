import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                             QPushButton, QFileDialog, QMessageBox, QDialog,
                             QGroupBox, QCheckBox, QDialogButtonBox, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QBrush, QPen, QIcon

# Carpeta de la aplicación: junto al .exe cuando está empaquetada (PyInstaller),
# o junto al script en desarrollo. Ahí viven config.json y logo.png.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Recursos incluidos dentro del ejecutable (por ejemplo icon.ico)
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)

# VLC portátil: si existe una carpeta "vlc" junto a la aplicación (con libvlc.dll
# y plugins), se usa en lugar de la instalación del sistema. Debe ir antes de importar vlc.
_PORTABLE_VLC = os.path.join(APP_DIR, "vlc")
if sys.platform.startswith("win") and os.path.isfile(os.path.join(_PORTABLE_VLC, "libvlc.dll")):
    os.environ.setdefault("PYTHON_VLC_LIB_PATH", os.path.join(_PORTABLE_VLC, "libvlc.dll"))
    os.environ.setdefault("PYTHON_VLC_MODULE_PATH", os.path.join(_PORTABLE_VLC, "plugins"))
    try:
        os.add_dll_directory(_PORTABLE_VLC)
    except (AttributeError, OSError):
        pass

import vlc

# ---------------------------------------------------------------------------
# Constantes y configuración
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LOGO_PATH = os.path.join(APP_DIR, "logo.png")

# Formatos de video conocidos y soportados por VLC
ALL_VIDEO_FORMATS = ['.mp4', '.m4v', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.f4v',
                     '.webm', '.mpg', '.mpeg', '.ts', '.m2ts', '.mts', '.3gp',
                     '.ogv', '.vob', '.divx', '.asf', '.rm', '.rmvb']
# Formatos marcados por defecto
DEFAULT_ENABLED_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']

QUEUED_PREFIX = "En cola: "
QUEUE_HEIGHT_RATIO = 0.18  # alto del panel de cola respecto a la pantalla
PREVIEW_DELAY_MS = 1200    # espera sin navegar antes de iniciar la vista previa (1-2 s)

FONT_FAMILY = '"Segoe UI", "Noto Sans", "DejaVu Sans", Arial, sans-serif'

MAIN_LIST_STYLE = f"""
    QListWidget {{
        font-family: {FONT_FAMILY};
        font-size: 28px;
        background-color: #121212;
        color: #f0f0f0;
        border: 2px solid #333333;
    }}
    QListWidget::item {{
        padding: 8px 14px;
    }}
    QListWidget::item:selected {{
        background-color: #1e88e5;
        color: white;
    }}
"""

QUEUE_LIST_STYLE = f"""
    QListWidget {{
        font-family: {FONT_FAMILY};
        font-size: 26px;
        background-color: rgba(0, 0, 0, 220);
        color: white;
        border: none;
    }}
    QListWidget::item {{
        padding: 8px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 50);
    }}
    QListWidget::item:selected {{
        background-color: rgba(30, 136, 229, 200);
    }}
"""


def load_config():
    config = {
        "directories": [],
        "extensions": list(DEFAULT_ENABLED_FORMATS),
        "normalize_volume": True,
    }
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            if isinstance(data.get("directories"), list):
                config["directories"] = [d for d in data["directories"] if isinstance(d, str)]
            if isinstance(data.get("extensions"), list):
                config["extensions"] = [e for e in data["extensions"] if isinstance(e, str)]
            if isinstance(data.get("normalize_volume"), bool):
                config["normalize_volume"] = data["normalize_volume"]
    except (OSError, ValueError):
        pass
    return config


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"No se pudo guardar la configuración: {e}")


def create_default_logo(path):
    """Genera un logo.png por defecto si no existe uno."""
    width, height = 900, 300
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#101018"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    gradient = QLinearGradient(0, 0, width, 0)
    gradient.setColorAt(0.0, QColor("#ff5f6d"))
    gradient.setColorAt(1.0, QColor("#ffc371"))

    painter.setPen(QPen(QBrush(gradient), 6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(12, 12, width - 24, height - 24, 30, 30)

    painter.setFont(QFont("Arial", 72, QFont.Weight.Bold))
    painter.setPen(QPen(QBrush(gradient), 1))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "VideoRockola")
    painter.end()

    pixmap.save(path, "PNG")


# ---------------------------------------------------------------------------
# Widgets auxiliares
# ---------------------------------------------------------------------------
class LogoLabel(QLabel):
    """Muestra una imagen escalada manteniendo la proporción."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(100, 60)

    def load(self, path):
        self._pixmap = QPixmap(path)
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._pixmap.isNull():
            self.setText("LOGO")
        else:
            self.setPixmap(self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))


class SettingsDialog(QDialog):
    """Diálogo de configuración: directorios, formatos, logo y volumen."""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumSize(660, 700)
        self.new_logo_path = None

        layout = QVBoxLayout(self)

        # --- Directorios ---
        dirs_box = QGroupBox("Directorios de videos musicales")
        dirs_layout = QVBoxLayout(dirs_box)
        self.dir_list = QListWidget()
        self.dir_list.addItems(config["directories"])
        dirs_layout.addWidget(self.dir_list)

        dir_buttons = QHBoxLayout()
        add_button = QPushButton("Agregar directorio…")
        add_button.clicked.connect(self.add_directory)
        remove_button = QPushButton("Quitar seleccionado")
        remove_button.clicked.connect(self.remove_directory)
        dir_buttons.addWidget(add_button)
        dir_buttons.addWidget(remove_button)
        dir_buttons.addStretch()
        dirs_layout.addLayout(dir_buttons)
        layout.addWidget(dirs_box, 2)

        # --- Formatos ---
        formats_box = QGroupBox("Formatos de video soportados")
        formats_layout = QVBoxLayout(formats_box)
        self.format_list = QListWidget()
        enabled = [e.lower() for e in config["extensions"]]
        all_formats = ALL_VIDEO_FORMATS + [e for e in enabled if e not in ALL_VIDEO_FORMATS]
        for ext in all_formats:
            item = QListWidgetItem(ext)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if ext in enabled
                               else Qt.CheckState.Unchecked)
            self.format_list.addItem(item)
        formats_layout.addWidget(self.format_list)

        format_buttons = QHBoxLayout()
        all_button = QPushButton("Marcar todos")
        all_button.clicked.connect(lambda: self.set_all_formats(Qt.CheckState.Checked))
        none_button = QPushButton("Desmarcar todos")
        none_button.clicked.connect(lambda: self.set_all_formats(Qt.CheckState.Unchecked))
        format_buttons.addWidget(all_button)
        format_buttons.addWidget(none_button)
        format_buttons.addStretch()
        formats_layout.addLayout(format_buttons)
        layout.addWidget(formats_box, 3)

        # --- Logo ---
        logo_box = QGroupBox("Logo (logo.png)")
        logo_layout = QHBoxLayout(logo_box)
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(240, 80)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setStyleSheet("border: 1px solid #888; background: #202020;")
        self.set_logo_preview(LOGO_PATH)
        logo_button = QPushButton("Cambiar logo…")
        logo_button.clicked.connect(self.choose_logo)
        logo_layout.addWidget(self.logo_preview)
        logo_layout.addWidget(logo_button)
        logo_layout.addStretch()
        layout.addWidget(logo_box)

        # --- Volumen ---
        self.normalize_check = QCheckBox(
            "Normalizar el volumen automáticamente (requiere reiniciar la aplicación)")
        self.normalize_check.setChecked(config["normalize_volume"])
        layout.addWidget(self.normalize_check)

        # --- Botones ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_logo_preview(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.logo_preview.setText("Sin logo")
        else:
            self.logo_preview.setPixmap(pixmap.scaled(
                self.logo_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def add_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar directorio de videos")
        if directory:
            directory = os.path.normpath(directory)
            existing = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
            if directory not in existing:
                self.dir_list.addItem(directory)

    def remove_directory(self):
        for item in self.dir_list.selectedItems():
            self.dir_list.takeItem(self.dir_list.row(item))

    def set_all_formats(self, state):
        for i in range(self.format_list.count()):
            self.format_list.item(i).setCheckState(state)

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar logo", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if path:
            self.new_logo_path = path
            self.set_logo_preview(path)

    def get_config(self):
        directories = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
        extensions = [self.format_list.item(i).text()
                      for i in range(self.format_list.count())
                      if self.format_list.item(i).checkState() == Qt.CheckState.Checked]
        return {
            "directories": directories,
            "extensions": extensions,
            "normalize_volume": self.normalize_check.isChecked(),
        }


class QueueListDialog(QDialog):
    video_selected = pyqtSignal(str)  # Se emite al elegir un video

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar a la cola")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        # Dimensiones de la pantalla
        screen = QApplication.primaryScreen().geometry()
        width = screen.width()
        height = int(screen.height() * QUEUE_HEIGHT_RATIO)

        # Posición en la parte inferior de la pantalla
        self.setGeometry(0, screen.height() - height, width, height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_list = QListWidget()
        self.video_list.setStyleSheet(QUEUE_LIST_STYLE)
        self.video_list.itemDoubleClicked.connect(self.select_video)
        layout.addWidget(self.video_list)

        self.videos = []
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide)
        self.hide_timer.setSingleShot(True)
        self.is_arrow_key_pressed = False

    def showEvent(self, event):
        super().showEvent(event)
        self.video_list.setFocus()
        self.hide_timer.start(5000)
        self.is_arrow_key_pressed = False

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.parent():
            self.parent().setFocus()
        self.is_arrow_key_pressed = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.video_list.currentItem()
            if current_item:
                self.select_video(current_item)
            event.accept()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            # Detener el temporizador mientras se navega
            self.hide_timer.stop()
            self.is_arrow_key_pressed = True
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.is_arrow_key_pressed = False
            self.hide_timer.start(5000)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        self.hide_timer.start(5000)
        self.is_arrow_key_pressed = False
        super().mousePressEvent(event)

    def load_videos(self, videos):
        self.video_list.clear()
        self.videos = list(videos)
        for video in self.videos:
            self.video_list.addItem(video["title"])

    def select_video(self, item):
        row = self.video_list.row(item)
        if 0 <= row < len(self.videos):
            self.video_selected.emit(self.videos[row]["path"])
            self.hide()


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class VideoRockola(QMainWindow):
    media_ended = pyqtSignal()  # Permite pasar el evento de VLC al hilo de Qt

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoRockola")
        self.setGeometry(100, 100, 1200, 800)

        self.config = load_config()

        # Logo por defecto si no existe
        if not os.path.exists(LOGO_PATH):
            try:
                create_default_logo(LOGO_PATH)
            except Exception as e:
                print(f"No se pudo crear el logo por defecto: {e}")

        # Widget central y layout principal:
        #   [ LOGO | VIDEO ]
        #   [ LISTA CANCIONES ]
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self._default_margins = self.main_layout.contentsMargins()

        self.top_layout = QHBoxLayout()

        self.logo_label = LogoLabel()
        self.logo_label.load(LOGO_PATH)

        self.video_frame = QWidget()
        self.video_frame.setMinimumSize(320, 180)
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setStyleSheet("background-color: black;")

        self.top_layout.addWidget(self.logo_label, 2)
        self.top_layout.addWidget(self.video_frame, 1)

        self.playlist = QListWidget()
        self.playlist.setStyleSheet(MAIN_LIST_STYLE)
        self.playlist.currentRowChanged.connect(self.play_selected)
        self.playlist.installEventFilter(self)

        self.main_layout.addLayout(self.top_layout, 2)
        self.main_layout.addWidget(self.playlist, 3)

        # Instancia de VLC (con normalización de volumen opcional)
        try:
            vlc_args = ['--verbose=2', '--no-video-title-show']
            if self.config["normalize_volume"]:
                vlc_args += ['--audio-filter=normvol',
                             '--norm-buff-size=20',
                             '--norm-max-level=1.5']
            self.instance = vlc.Instance(vlc_args)
            self.mediaplayer = self.instance.media_player_new()
            self.mediaplayer.video_set_format("I420", 800, 600, 800)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo inicializar VLC: {str(e)}")
            sys.exit(1)

        # Salida de video según la plataforma (el widget ya está dentro del layout)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        if sys.platform.startswith('win'):
            self.mediaplayer.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform.startswith('linux'):
            self.mediaplayer.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform.startswith('darwin'):
            self.mediaplayer.set_nsobject(int(self.video_frame.winId()))

        # Temporizador de vista previa
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.stop_preview)
        self.preview_duration = 5000  # 5 segundos

        # La vista previa solo arranca cuando el usuario deja de navegar
        self.preview_delay_timer = QTimer()
        self.preview_delay_timer.setSingleShot(True)
        self.preview_delay_timer.timeout.connect(self.start_pending_preview)
        self.pending_preview_row = -1
        self.preview_token = 0     # invalida temporizadores de vistas previas anteriores
        self.current_path = None   # ruta del video cargado en el reproductor

        # Estado del reproductor
        self.current_media = None
        self.is_playing = False
        self.videos = []
        self.is_fullscreen = False

        # Cola de reproducción
        self.video_queue = []
        self.queue_list_dialog = QueueListDialog(self)
        self.queue_list_dialog.video_selected.connect(self.add_to_queue)

        # Fin de video (VLC lo emite desde otro hilo; se reenvía con una señal de Qt)
        self.media_ended.connect(self.on_media_end)
        self.mediaplayer.event_manager().event_attach(
            vlc.EventType.MediaPlayerEndReached, lambda event: self.media_ended.emit())

        self.load_videos()

    # --- Configuración -----------------------------------------------------
    def open_settings(self):
        if self.is_fullscreen:
            return
        dialog = SettingsDialog(self, self.config)
        if dialog.exec():
            old_normalize = self.config["normalize_volume"]
            self.config = dialog.get_config()
            save_config(self.config)

            if dialog.new_logo_path:
                self.change_logo(dialog.new_logo_path)

            self.load_videos()

            if old_normalize != self.config["normalize_volume"]:
                QMessageBox.information(
                    self, "Volumen",
                    "El cambio en la normalización de volumen se aplicará al reiniciar la aplicación.")
        self.playlist.setFocus()

    def change_logo(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Logo", "No se pudo cargar la imagen seleccionada.")
            return
        if not pixmap.save(LOGO_PATH, "PNG"):
            QMessageBox.warning(self, "Logo", "No se pudo guardar logo.png.")
            return
        self.logo_label.load(LOGO_PATH)

    # --- Carga de videos ---------------------------------------------------
    def load_videos(self):
        self.playlist.clear()
        self.videos = []
        self.video_queue = []

        extensions = tuple(e.lower() for e in self.config["extensions"])
        seen = set()

        for directory in self.config["directories"]:
            if not os.path.isdir(directory):
                continue
            try:
                filenames = os.listdir(directory)
            except OSError:
                continue
            for filename in filenames:
                if extensions and filename.lower().endswith(extensions):
                    video_path = os.path.join(directory, filename)
                    if video_path in seen:
                        continue
                    seen.add(video_path)
                    video_title = os.path.splitext(filename)[0]
                    self.videos.append({"title": video_title, "path": video_path})

        # Orden ascendente de todos los videos encontrados (de todos los directorios)
        self.videos.sort(key=lambda v: (v["title"].lower(), v["path"].lower()))
        for video in self.videos:
            self.playlist.addItem(video["title"])

        if not self.videos:
            item = QListWidgetItem("No hay videos. Presiona P para configurar los directorios.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.playlist.addItem(item)

        self.focus_playlist()

    def focus_playlist(self):
        """Da el foco a la lista si tiene al menos un video."""
        if not self.videos:
            return
        self.playlist.setEnabled(True)
        self.playlist.setFocus()
        if self.playlist.currentRow() < 0:
            # Marca el primer elemento sin disparar la vista previa
            self.playlist.blockSignals(True)
            self.playlist.setCurrentRow(0)
            self.playlist.blockSignals(False)

    # --- Cola --------------------------------------------------------------
    def show_queue_list(self):
        if self.videos and self.current_media:
            self.queue_list_dialog.load_videos(self.videos)
            self.queue_list_dialog.show()
            self.queue_list_dialog.raise_()

    def add_to_queue(self, video_path):
        video_title = os.path.splitext(os.path.basename(video_path))[0]
        self.video_queue.append({"title": video_title, "path": video_path})
        self.playlist.addItem(f"{QUEUED_PREFIX}{video_title}")

    def on_media_end(self):
        if not self.is_fullscreen:
            # Terminó una vista previa: no tocar el foco ni la navegación
            self.is_playing = False
            self.preview_timer.stop()
            return
        # Al terminar un video, reproducir el siguiente de la cola
        if self.play_next_queued_video():
            return
        # Sin cola: volver a la lista y darle el foco
        if self.queue_list_dialog.isVisible():
            self.queue_list_dialog.hide()
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.focus_playlist()

    def play_next_queued_video(self):
        if self.video_queue:
            next_video = self.video_queue.pop(0)
            for i in range(self.playlist.count()):
                if self.playlist.item(i).text().startswith(QUEUED_PREFIX):
                    self.playlist.takeItem(i)
                    break
            self.play_video(next_video["path"])
            return True
        return False

    # --- Reproducción ------------------------------------------------------
    def play_video(self, video_path):
        try:
            self.current_media = self.instance.media_new(video_path)
            self.current_path = video_path
            self.mediaplayer.set_media(self.current_media)
            self.mediaplayer.play()
            self.is_playing = True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reproducir el video: {str(e)}")

    def play_selected(self, row):
        if self.is_fullscreen:
            if 0 <= row < len(self.videos):
                self.play_video(self.videos[row]["path"])
            return

        # Navegando: se cancela la vista previa en curso (sin cargar nada nuevo)
        # y se espera a que el usuario deje de moverse por la lista.
        self.cancel_pending_preview()
        if self.is_playing:
            self.mediaplayer.set_pause(1)
            self.is_playing = False
        if 0 <= row < len(self.videos):
            self.pending_preview_row = row
            self.preview_delay_timer.start(PREVIEW_DELAY_MS)

    def cancel_pending_preview(self):
        self.preview_delay_timer.stop()
        self.preview_timer.stop()
        self.pending_preview_row = -1
        self.preview_token += 1

    def start_pending_preview(self):
        row = self.pending_preview_row
        self.pending_preview_row = -1
        if self.is_fullscreen or not (0 <= row < len(self.videos)):
            return
        self.preview_token += 1
        token = self.preview_token
        self.play_video(self.videos[row]["path"])
        self.seek_to_middle(token, 0)

    def seek_to_middle(self, token, tries):
        """Espera sin bloquear a que VLC conozca la duración y salta a la mitad."""
        if token != self.preview_token or self.is_fullscreen:
            return  # La vista previa fue reemplazada o cancelada
        if self.mediaplayer.get_length() > 0:
            self.mediaplayer.set_position(0.5)
            self.preview_timer.start(self.preview_duration)
        elif tries < 30:
            QTimer.singleShot(100, lambda: self.seek_to_middle(token, tries + 1))
        else:
            self.preview_timer.start(self.preview_duration)

    def play_pause(self):
        if self.current_media:
            if self.is_playing:
                self.mediaplayer.set_pause(1)
                self.is_playing = False
            else:
                self.mediaplayer.play()
                self.is_playing = True

    def stop_preview(self):
        if self.is_playing and not self.is_fullscreen:
            self.mediaplayer.set_pause(1)
            self.is_playing = False
        self.preview_timer.stop()

    # --- Pantalla completa -------------------------------------------------
    def enter_fullscreen(self):
        self.is_fullscreen = True
        self.logo_label.hide()
        self.playlist.hide()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.showFullScreen()
        self.mediaplayer.set_position(0.0)
        self.mediaplayer.play()
        self.is_playing = True
        self.preview_timer.stop()
        self.playlist.setEnabled(False)
        self.setFocus()

    def exit_fullscreen(self):
        self.is_fullscreen = False
        self.showNormal()
        self.main_layout.setContentsMargins(self._default_margins)
        self.logo_label.show()
        self.playlist.show()
        self.mediaplayer.set_pause(1)
        self.is_playing = False
        self.playlist.setEnabled(True)
        self.focus_playlist()

    # --- Teclado -----------------------------------------------------------
    def eventFilter(self, obj, event):
        # La lista consume algunas teclas; se reenvían a la ventana principal
        if obj is self.playlist and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_P, Qt.Key.Key_Space,
                               Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_P:
            if not self.is_fullscreen:
                self.open_settings()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if not self.is_fullscreen:
                self.cancel_pending_preview()
                # Reproducir el elemento seleccionado si aún no es el video cargado
                row = self.playlist.currentRow()
                if 0 <= row < len(self.videos):
                    path = self.videos[row]["path"]
                    if path != self.current_path:
                        self.play_video(path)
                if self.current_media:
                    self.enter_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            if self.is_fullscreen:
                if self.queue_list_dialog.isVisible():
                    self.queue_list_dialog.hide()
                else:
                    if self.video_queue:
                        self.play_next_queued_video()
                    else:
                        self.exit_fullscreen()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self.is_fullscreen and self.current_media:
                self.show_queue_list()
        elif event.key() == Qt.Key.Key_Space:
            if self.current_media:
                self.play_pause()
        else:
            super().keyPressEvent(event)


def find_app_icon():
    """Busca icon.ico (o icon.png / logo.png como alternativa) para la ventana."""
    for folder in (APP_DIR, RESOURCE_DIR):
        for name in ("icon.ico", "icon.png", "logo.png"):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        # Para que la barra de tareas use el icono de la aplicación y no el de Python
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("videorockola.app")
        except Exception:
            pass

    app = QApplication(sys.argv)
    _icon_path = find_app_icon()
    if _icon_path:
        app.setWindowIcon(QIcon(_icon_path))
    window = VideoRockola()
    window.show()
    window.activateWindow()
    window.focus_playlist()
    # Primera ejecución: abrir la configuración si aún no hay directorios
    if not window.config["directories"]:
        QTimer.singleShot(300, window.open_settings)
    sys.exit(app.exec())
