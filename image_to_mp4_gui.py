#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#source: github.com/zeittresor
"""
image_to_mp4_gui.py

Improved, beginner-friendly GUI tool (PyQt5) to turn a list of images into an MP4 video.

Dependencies:
    pip install PyQt5 Pillow opencv-python numpy

Features:
- Drag & Drop images and folders (non-recursive)
- Add files / add folder via dialogs
- Reorder by dragging inside the list
- Remove selected / clear list
- Output size + frame interval (ms) settings
- EXIF auto-rotate support
- Center-fit with black padding (keeps aspect ratio)
- Progress bar + status text + cancel button
- Multi-language UI switcher via radio buttons:
  German, English, French, Spanish, Russian
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QLocale
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLabel,
    QSpinBox, QProgressBar, QMessageBox, QAbstractItemView,
    QGroupBox, QRadioButton, QButtonGroup, QFormLayout
)

SUPPORTED_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')


# --------------------------- i18n ---------------------------

LANGS = ("de", "en", "fr", "es", "ru")

I18N: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "Images → MP4 (Drag & Drop)",
        "btn_add_files": "Add files…",
        "btn_add_folder": "Add folder…",
        "btn_remove": "Remove selected",
        "btn_clear": "Clear list",
        "lbl_interval": "Interval (ms):",
        "lbl_width": "Width:",
        "lbl_height": "Height:",
        "btn_choose_out": "Choose output…",
        "lbl_no_out": "No output file selected",
        "btn_create": "Create video",
        "btn_cancel": "Cancel",
        "status_ready": "Ready.",
        "status_added": "Added {added} new item(s).",
        "msg_skipped": "Skipped {n} image(s) that could not be opened.",
        "msg_skipped_examples": "Examples:\n{items}",
        "status_building": "Creating video…",
        "status_cancel_requested": "Cancel requested…",
        "status_done": "Saved: {path}",
        "status_cancelled": "Cancelled.",
        "dlg_pick_images": "Select images",
        "dlg_pick_folder": "Select folder",
        "dlg_save_as": "Save as",
        "filter_images": "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        "filter_mp4": "MP4 Video (*.mp4)",
        "msg_no_out_title": "No output file",
        "msg_no_out_text": "Please choose an output file first.",
        "msg_no_images_title": "No images",
        "msg_no_images_text": "Please add images first (Drag & Drop or Add files).",
        "msg_done_title": "Done",
        "msg_error_title": "Error",
        "msg_cancel_title": "Cancelled",
        "msg_writer_fail": "Could not open video writer. Check output path and codec availability.",
        "msg_open_fail": "Could not open image:\n{path}\n\n{err}",
        "msg_generic_error": "Error: {err}",
        "msg_cancel_text": "Video creation was cancelled.",
        "group_settings": "Settings",
        "group_output": "Output",
        "group_language": "Language",
        "tip_list": "Drag & drop images or folders here. You can reorder entries by dragging them.",
        "tip_interval": "How long each image is shown (in milliseconds).",
        "tip_size": "Target video size. Images are scaled to fit and padded with black bars if needed.",
        "tip_out": "Choose where the MP4 should be saved.",
        "tip_cancel": "Stop the current render (safe cancel).",
    },
    "de": {
        "title": "Bilder → MP4 (Drag & Drop)",
        "btn_add_files": "Dateien hinzufügen…",
        "btn_add_folder": "Ordner hinzufügen…",
        "btn_remove": "Ausgewählte entfernen",
        "btn_clear": "Liste leeren",
        "lbl_interval": "Intervall (ms):",
        "lbl_width": "Breite:",
        "lbl_height": "Höhe:",
        "btn_choose_out": "Zieldatei auswählen…",
        "lbl_no_out": "Noch keine Zieldatei gewählt",
        "btn_create": "Video erstellen",
        "btn_cancel": "Abbrechen",
        "status_ready": "Bereit.",
        "status_added": "{added} neue Datei(en) hinzugefügt.",
        "msg_skipped": "{n} Bild(er) wurden übersprungen (konnten nicht geöffnet werden).",
        "msg_skipped_examples": "Beispiele:\n{items}",
        "status_building": "Erstelle Video…",
        "status_cancel_requested": "Abbruch angefordert…",
        "status_done": "Gespeichert: {path}",
        "status_cancelled": "Abgebrochen.",
        "dlg_pick_images": "Bilder wählen",
        "dlg_pick_folder": "Ordner wählen",
        "dlg_save_as": "Speichern als",
        "filter_images": "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        "filter_mp4": "MP4 Video (*.mp4)",
        "msg_no_out_title": "Keine Zieldatei",
        "msg_no_out_text": "Bitte wähle zuerst eine Zieldatei zum Speichern.",
        "msg_no_images_title": "Keine Bilder",
        "msg_no_images_text": "Bitte füge zuerst Bilder hinzu (Drag & Drop oder Dateien hinzufügen).",
        "msg_done_title": "Fertig",
        "msg_error_title": "Fehler",
        "msg_cancel_title": "Abgebrochen",
        "msg_writer_fail": "VideoWriter konnte nicht geöffnet werden. Prüfe Ausgabepfad und Codec-Verfügbarkeit.",
        "msg_open_fail": "Konnte Bild nicht öffnen:\n{path}\n\n{err}",
        "msg_generic_error": "Fehler: {err}",
        "msg_cancel_text": "Video-Erstellung wurde abgebrochen.",
        "group_settings": "Einstellungen",
        "group_output": "Ausgabe",
        "group_language": "Sprache",
        "tip_list": "Ziehe Bilder oder Ordner hier hinein. Du kannst Einträge per Drag & Drop umsortieren.",
        "tip_interval": "Wie lange jedes Bild angezeigt wird (in Millisekunden).",
        "tip_size": "Zielgröße des Videos. Bilder werden passend skaliert und ggf. mit schwarzen Balken aufgefüllt.",
        "tip_out": "Wähle, wo die MP4-Datei gespeichert werden soll.",
        "tip_cancel": "Aktuelles Rendern stoppen (sicherer Abbruch).",
    },
    "fr": {
        "title": "Images → MP4 (Glisser-déposer)",
        "btn_add_files": "Ajouter des fichiers…",
        "btn_add_folder": "Ajouter un dossier…",
        "btn_remove": "Supprimer la sélection",
        "btn_clear": "Vider la liste",
        "lbl_interval": "Intervalle (ms) :",
        "lbl_width": "Largeur :",
        "lbl_height": "Hauteur :",
        "btn_choose_out": "Choisir la sortie…",
        "lbl_no_out": "Aucun fichier de sortie sélectionné",
        "btn_create": "Créer la vidéo",
        "btn_cancel": "Annuler",
        "status_ready": "Prêt.",
        "status_added": "{added} élément(s) ajouté(s).",
        "msg_skipped": "{n} image(s) ignorée(s) (impossible à ouvrir).",
        "msg_skipped_examples": "Exemples :\n{items}",
        "status_building": "Création de la vidéo…",
        "status_cancel_requested": "Annulation demandée…",
        "status_done": "Enregistré : {path}",
        "status_cancelled": "Annulé.",
        "dlg_pick_images": "Sélectionner des images",
        "dlg_pick_folder": "Sélectionner un dossier",
        "dlg_save_as": "Enregistrer sous",
        "filter_images": "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        "filter_mp4": "Vidéo MP4 (*.mp4)",
        "msg_no_out_title": "Pas de fichier de sortie",
        "msg_no_out_text": "Veuillez d'abord choisir un fichier de sortie.",
        "msg_no_images_title": "Aucune image",
        "msg_no_images_text": "Veuillez d'abord ajouter des images (glisser-déposer ou Ajouter).",
        "msg_done_title": "Terminé",
        "msg_error_title": "Erreur",
        "msg_cancel_title": "Annulé",
        "msg_writer_fail": "Impossible d'ouvrir le writer vidéo. Vérifiez le chemin de sortie et le codec.",
        "msg_open_fail": "Impossible d'ouvrir l'image :\n{path}\n\n{err}",
        "msg_generic_error": "Erreur : {err}",
        "msg_cancel_text": "La création de la vidéo a été annulée.",
        "group_settings": "Paramètres",
        "group_output": "Sortie",
        "group_language": "Langue",
        "tip_list": "Glissez-déposez des images ou des dossiers ici. Vous pouvez réorganiser en faisant glisser.",
        "tip_interval": "Durée d'affichage de chaque image (en millisecondes).",
        "tip_size": "Taille cible de la vidéo. Les images sont ajustées et complétées par des bandes noires si besoin.",
        "tip_out": "Choisissez où enregistrer le MP4.",
        "tip_cancel": "Arrêter le rendu en cours (annulation sûre).",
    },
    "es": {
        "title": "Imágenes → MP4 (Arrastrar y soltar)",
        "btn_add_files": "Añadir archivos…",
        "btn_add_folder": "Añadir carpeta…",
        "btn_remove": "Quitar seleccionados",
        "btn_clear": "Vaciar lista",
        "lbl_interval": "Intervalo (ms):",
        "lbl_width": "Ancho:",
        "lbl_height": "Alto:",
        "btn_choose_out": "Elegir salida…",
        "lbl_no_out": "No se ha seleccionado archivo de salida",
        "btn_create": "Crear vídeo",
        "btn_cancel": "Cancelar",
        "status_ready": "Listo.",
        "status_added": "Se añadieron {added} elemento(s).",
        "msg_skipped": "Se omitieron {n} imagen(es) (no se pudieron abrir).",
        "msg_skipped_examples": "Ejemplos:\n{items}",
        "status_building": "Creando vídeo…",
        "status_cancel_requested": "Cancelación solicitada…",
        "status_done": "Guardado: {path}",
        "status_cancelled": "Cancelado.",
        "dlg_pick_images": "Seleccionar imágenes",
        "dlg_pick_folder": "Seleccionar carpeta",
        "dlg_save_as": "Guardar como",
        "filter_images": "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        "filter_mp4": "Vídeo MP4 (*.mp4)",
        "msg_no_out_title": "Sin archivo de salida",
        "msg_no_out_text": "Primero elige un archivo de salida.",
        "msg_no_images_title": "Sin imágenes",
        "msg_no_images_text": "Primero añade imágenes (arrastrar y soltar o Añadir).",
        "msg_done_title": "Hecho",
        "msg_error_title": "Error",
        "msg_cancel_title": "Cancelado",
        "msg_writer_fail": "No se pudo abrir el escritor de vídeo. Revisa la ruta de salida y el códec.",
        "msg_open_fail": "No se pudo abrir la imagen:\n{path}\n\n{err}",
        "msg_generic_error": "Error: {err}",
        "msg_cancel_text": "La creación del vídeo fue cancelada.",
        "group_settings": "Ajustes",
        "group_output": "Salida",
        "group_language": "Idioma",
        "tip_list": "Arrastra y suelta imágenes o carpetas aquí. Puedes reordenar arrastrando.",
        "tip_interval": "Cuánto tiempo se muestra cada imagen (en milisegundos).",
        "tip_size": "Tamaño objetivo del vídeo. Las imágenes se ajustan y se rellenan con negro si hace falta.",
        "tip_out": "Elige dónde guardar el MP4.",
        "tip_cancel": "Detener el render actual (cancelación segura).",
    },
    "ru": {
        "title": "Изображения → MP4 (Drag & Drop)",
        "btn_add_files": "Добавить файлы…",
        "btn_add_folder": "Добавить папку…",
        "btn_remove": "Удалить выбранные",
        "btn_clear": "Очистить список",
        "lbl_interval": "Интервал (мс):",
        "lbl_width": "Ширина:",
        "lbl_height": "Высота:",
        "btn_choose_out": "Выбрать файл…",
        "lbl_no_out": "Файл вывода не выбран",
        "btn_create": "Создать видео",
        "btn_cancel": "Отмена",
        "status_ready": "Готово.",
        "status_added": "Добавлено: {added}.",
        "msg_skipped": "Пропущено изображений (не удалось открыть): {n}.",
        "msg_skipped_examples": "Примеры:\n{items}",
        "status_building": "Создание видео…",
        "status_cancel_requested": "Запрошена отмена…",
        "status_done": "Сохранено: {path}",
        "status_cancelled": "Отменено.",
        "dlg_pick_images": "Выбрать изображения",
        "dlg_pick_folder": "Выбрать папку",
        "dlg_save_as": "Сохранить как",
        "filter_images": "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        "filter_mp4": "Видео MP4 (*.mp4)",
        "msg_no_out_title": "Файл вывода не выбран",
        "msg_no_out_text": "Сначала выберите файл для сохранения.",
        "msg_no_images_title": "Нет изображений",
        "msg_no_images_text": "Сначала добавьте изображения (Drag & Drop или Добавить).",
        "msg_done_title": "Готово",
        "msg_error_title": "Ошибка",
        "msg_cancel_title": "Отменено",
        "msg_writer_fail": "Не удалось открыть VideoWriter. Проверьте путь сохранения и наличие кодека.",
        "msg_open_fail": "Не удалось открыть изображение:\n{path}\n\n{err}",
        "msg_generic_error": "Ошибка: {err}",
        "msg_cancel_text": "Создание видео было отменено.",
        "group_settings": "Настройки",
        "group_output": "Вывод",
        "group_language": "Язык",
        "tip_list": "Перетащите изображения или папки сюда. Порядок можно менять перетаскиванием.",
        "tip_interval": "Сколько показывать каждое изображение (в миллисекундах).",
        "tip_size": "Размер выходного видео. Изображения масштабируются и при необходимости дополняются черными полями.",
        "tip_out": "Выберите, куда сохранить MP4.",
        "tip_cancel": "Остановить текущий рендер (безопасная отмена).",
    },
}


def pick_default_lang() -> str:
    # Try to match system locale to our supported languages
    loc = QLocale.system().name().lower()  # e.g., "de_de"
    for lang in LANGS:
        if loc.startswith(lang):
            return lang
    return "en"


# --------------------------- Helpers ---------------------------

def norm_path(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def collect_images_from_folder(folder: str) -> List[str]:
    try:
        names = sorted(os.listdir(folder))
    except Exception:
        return []
    out: List[str] = []
    for fname in names:
        fp = os.path.join(folder, fname)
        if os.path.isfile(fp) and fname.lower().endswith(SUPPORTED_EXTS):
            out.append(fp)
    return out


# --------------------------- Widgets ---------------------------

class ImageListWidget(QListWidget):
    def __init__(self, main_window: "MainWindow"):
        super().__init__(main_window)
        self._main = main_window
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            paths: List[str] = []
            for url in e.mimeData().urls():
                p = url.toLocalFile()
                if not p:
                    continue
                if os.path.isdir(p):
                    paths.extend(collect_images_from_folder(p))
                elif p.lower().endswith(SUPPORTED_EXTS) and os.path.isfile(p):
                    paths.append(p)

            if paths:
                self._main.add_images(paths)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class VideoWorker(QThread):
    progress = pyqtSignal(int)                   # 0..100
    step = pyqtSignal(int, int, str)             # idx, total, path
    finished = pyqtSignal(bool, str, str)        # ok, code, detail

    def __init__(self, image_paths: List[str], out_path: str, width: int, height: int, interval_ms: int):
        super().__init__()
        self.skipped: List[str] = []
        self.image_paths = image_paths
        self.out_path = out_path
        self.width = width
        self.height = height
        self.interval_ms = interval_ms

    def run(self):
        try:
            if not self.image_paths:
                self.finished.emit(False, "no_images", "")
                return

            fps = 1000.0 / max(1, self.interval_ms)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(self.out_path, fourcc, fps, (self.width, self.height))
            if not writer.isOpened():
                self.finished.emit(False, "writer_open_failed", "")
                return

            total = len(self.image_paths)
            processed = 0

            for idx, p in enumerate(self.image_paths, start=1):
                if self.isInterruptionRequested():
                    writer.release()
                    self.finished.emit(False, "cancelled", "")
                    return

                self.step.emit(idx, total, p)

                try:
                    img = ImageOps.exif_transpose(Image.open(p)).convert("RGBA")
                except Exception as e:
                    self.skipped.append(p)
                    processed += 1
                    self.progress.emit(int(processed / total * 100))
                    continue

                img_w, img_h = img.size
                target_w, target_h = self.width, self.height

                # Scale to fit while preserving aspect ratio
                scale = min(target_w / max(1, img_w), target_h / max(1, img_h))
                new_w = max(1, int(round(img_w * scale)))
                new_h = max(1, int(round(img_h * scale)))

                resized = img.resize((new_w, new_h), resample=Image.LANCZOS)

                # Composite on black background and center
                background = Image.new("RGB", (target_w, target_h), (0, 0, 0))
                paste_x = (target_w - new_w) // 2
                paste_y = (target_h - new_h) // 2
                background.paste(resized, (paste_x, paste_y), resized)

                frame = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
                writer.write(frame)

                processed += 1
                self.progress.emit(int(processed / total * 100))

            writer.release()
            self.finished.emit(True, "done", self.out_path)
        except Exception as e:
            self.finished.emit(False, "error", str(e))


# --------------------------- Main Window ---------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.lang: str = pick_default_lang()
        self._t = I18N[self.lang]

        self.out_path: Optional[str] = None
        self.worker: Optional[VideoWorker] = None

        self._build_ui()
        self.apply_language(self.lang)

    def tr(self, key: str, **kwargs) -> str:
        text = self._t.get(key, I18N["en"].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def _build_ui(self):
        self.setWindowTitle(self.tr("title"))
        self.resize(760, 560)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout()
        central.setLayout(root)

        # Image list
        self.list_widget = ImageListWidget(self)
        self.list_widget.setToolTip(self.tr("tip_list"))
        root.addWidget(self.list_widget, 1)

        # Buttons row
        row_buttons = QHBoxLayout()
        self.btn_add_files = QPushButton()
        self.btn_add_files.clicked.connect(self.on_add_files)
        row_buttons.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton()
        self.btn_add_folder.clicked.connect(self.on_add_folder)
        row_buttons.addWidget(self.btn_add_folder)

        self.btn_remove = QPushButton()
        self.btn_remove.clicked.connect(self.on_remove_selected)
        row_buttons.addWidget(self.btn_remove)

        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self.on_clear)
        row_buttons.addWidget(self.btn_clear)

        root.addLayout(row_buttons)

        # Settings + language in a horizontal split
        row_panels = QHBoxLayout()

        # Settings group
        self.group_settings = QGroupBox()
        form = QFormLayout()
        self.group_settings.setLayout(form)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 600000)
        self.spin_interval.setValue(40)
        self.spin_interval.setToolTip(self.tr("tip_interval"))

        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 8192)
        self.spin_width.setValue(512)
        self.spin_width.setToolTip(self.tr("tip_size"))

        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 8192)
        self.spin_height.setValue(512)
        self.spin_height.setToolTip(self.tr("tip_size"))

        self.lbl_interval = QLabel()
        self.lbl_width = QLabel()
        self.lbl_height = QLabel()

        form.addRow(self.lbl_interval, self.spin_interval)
        form.addRow(self.lbl_width, self.spin_width)
        form.addRow(self.lbl_height, self.spin_height)

        row_panels.addWidget(self.group_settings, 2)

        # Language group
        self.group_language = QGroupBox()
        lang_layout = QVBoxLayout()
        self.group_language.setLayout(lang_layout)

        self.lang_group = QButtonGroup(self)
        self.rb_de = QRadioButton("Deutsch")
        self.rb_en = QRadioButton("English")
        self.rb_fr = QRadioButton("Français")
        self.rb_es = QRadioButton("Español")
        self.rb_ru = QRadioButton("Русский")

        self.lang_group.addButton(self.rb_de)
        self.lang_group.addButton(self.rb_en)
        self.lang_group.addButton(self.rb_fr)
        self.lang_group.addButton(self.rb_es)
        self.lang_group.addButton(self.rb_ru)

        lang_layout.addWidget(self.rb_de)
        lang_layout.addWidget(self.rb_en)
        lang_layout.addWidget(self.rb_fr)
        lang_layout.addWidget(self.rb_es)
        lang_layout.addWidget(self.rb_ru)
        lang_layout.addStretch(1)

        self.rb_de.toggled.connect(lambda on: on and self.apply_language("de"))
        self.rb_en.toggled.connect(lambda on: on and self.apply_language("en"))
        self.rb_fr.toggled.connect(lambda on: on and self.apply_language("fr"))
        self.rb_es.toggled.connect(lambda on: on and self.apply_language("es"))
        self.rb_ru.toggled.connect(lambda on: on and self.apply_language("ru"))

        row_panels.addWidget(self.group_language, 1)
        root.addLayout(row_panels)

        # Output group
        self.group_output = QGroupBox()
        out_layout = QHBoxLayout()
        self.group_output.setLayout(out_layout)

        self.btn_choose_out = QPushButton()
        self.btn_choose_out.clicked.connect(self.on_choose_save)
        self.btn_choose_out.setToolTip(self.tr("tip_out"))
        out_layout.addWidget(self.btn_choose_out)

        self.label_out = QLabel()
        self.label_out.setTextInteractionFlags(Qt.TextSelectableByMouse)
        out_layout.addWidget(self.label_out, 1)

        root.addWidget(self.group_output)

        # Create / Progress / Cancel
        row_create = QHBoxLayout()
        self.btn_create = QPushButton()
        self.btn_create.clicked.connect(self.on_create_video)
        row_create.addWidget(self.btn_create)

        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self.on_cancel)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setToolTip(self.tr("tip_cancel"))
        row_create.addWidget(self.btn_cancel)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        row_create.addWidget(self.progress, 1)

        root.addLayout(row_create)

        # Status bar
        self.status = self.statusBar()
        self.status.showMessage(self.tr("status_ready"))

    # -------- i18n apply --------

    def apply_language(self, lang: str):
        if lang not in LANGS:
            lang = "en"
        self.lang = lang
        self._t = I18N.get(lang, I18N["en"])

        # Window / groups
        self.setWindowTitle(self.tr("title"))
        self.group_settings.setTitle(self.tr("group_settings"))
        self.group_output.setTitle(self.tr("group_output"))
        self.group_language.setTitle(self.tr("group_language"))

        # Labels / buttons
        self.btn_add_files.setText(self.tr("btn_add_files"))
        self.btn_add_folder.setText(self.tr("btn_add_folder"))
        self.btn_remove.setText(self.tr("btn_remove"))
        self.btn_clear.setText(self.tr("btn_clear"))
        self.btn_choose_out.setText(self.tr("btn_choose_out"))
        self.btn_create.setText(self.tr("btn_create"))
        self.btn_cancel.setText(self.tr("btn_cancel"))

        self.lbl_interval.setText(self.tr("lbl_interval"))
        self.lbl_width.setText(self.tr("lbl_width"))
        self.lbl_height.setText(self.tr("lbl_height"))

        # Tooltips
        self.list_widget.setToolTip(self.tr("tip_list"))
        self.spin_interval.setToolTip(self.tr("tip_interval"))
        self.spin_width.setToolTip(self.tr("tip_size"))
        self.spin_height.setToolTip(self.tr("tip_size"))
        self.btn_choose_out.setToolTip(self.tr("tip_out"))
        self.btn_cancel.setToolTip(self.tr("tip_cancel"))

        # Output label fallback
        if not self.out_path:
            self.label_out.setText(self.tr("lbl_no_out"))

        # Status
        self.status.showMessage(self.tr("status_ready"), 4000)

        # Set the right radio button without retrigger loops
        mapping = {"de": self.rb_de, "en": self.rb_en, "fr": self.rb_fr, "es": self.rb_es, "ru": self.rb_ru}
        rb = mapping.get(lang)
        if rb and not rb.isChecked():
            rb.blockSignals(True)
            rb.setChecked(True)
            rb.blockSignals(False)

    # -------- list handling --------

    def add_images(self, paths: List[str]):
        # De-duplicate paths while keeping order
        existing = {norm_path(self.list_widget.item(i).text()) for i in range(self.list_widget.count())}
        added = 0
        for p in paths:
            if not p:
                continue
            if os.path.isdir(p):
                for fp in collect_images_from_folder(p):
                    key = norm_path(fp)
                    if key in existing:
                        continue
                    self._add_item(fp)
                    existing.add(key)
                    added += 1
            else:
                if not (os.path.isfile(p) and p.lower().endswith(SUPPORTED_EXTS)):
                    continue
                key = norm_path(p)
                if key in existing:
                    continue
                self._add_item(p)
                existing.add(key)
                added += 1

        if added:
            self.status.showMessage(self.tr("status_added", added=added), 2500)

    def _add_item(self, p: str):
        item = QListWidgetItem(p)
        item.setToolTip(p)
        self.list_widget.addItem(item)

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("dlg_pick_images"), "", self.tr("filter_images")
        )
        if files:
            self.add_images(files)

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("dlg_pick_folder"))
        if folder:
            self.add_images([folder])

    def on_remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def on_clear(self):
        self.list_widget.clear()
        self.progress.setValue(0)
        self.status.showMessage(self.tr("status_ready"), 3000)

    # -------- output + rendering --------

    def on_choose_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("dlg_save_as"), "output.mp4", self.tr("filter_mp4")
        )
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.out_path = path
            self.label_out.setText(self.out_path)

    def set_busy(self, busy: bool):
        self.btn_create.setEnabled(not busy)
        self.btn_add_files.setEnabled(not busy)
        self.btn_add_folder.setEnabled(not busy)
        self.btn_remove.setEnabled(not busy)
        self.btn_clear.setEnabled(not busy)
        self.btn_choose_out.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.group_language.setEnabled(not busy)

    def on_create_video(self):
        if not self.out_path:
            QMessageBox.warning(self, self.tr("msg_no_out_title"), self.tr("msg_no_out_text"))
            return

        image_paths = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if not image_paths:
            QMessageBox.warning(self, self.tr("msg_no_images_title"), self.tr("msg_no_images_text"))
            return

        width = int(self.spin_width.value())
        height = int(self.spin_height.value())
        interval_ms = int(self.spin_interval.value())

        self.progress.setValue(0)
        self.status.showMessage(self.tr("status_building"))
        self.set_busy(True)

        self.worker = VideoWorker(image_paths, self.out_path, width, height, interval_ms)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.step.connect(self.on_worker_step)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.status.showMessage(self.tr("status_cancel_requested"))
            self.worker.requestInterruption()

    def on_worker_step(self, idx: int, total: int, path: str):
        base = os.path.basename(path)
        self.status.showMessage(f"{self.tr('status_building')}  {idx}/{total}: {base}")

    def on_worker_finished(self, ok: bool, code: str, detail: str):
        self.set_busy(False)
        if code == "done" and ok:
            msg = self.tr("status_done", path=detail)

            examples = ""
            if self.worker is not None and getattr(self.worker, "skipped", None):
                skipped = len(self.worker.skipped)
                if skipped:
                    sample = [os.path.basename(p) for p in self.worker.skipped[:10]]
                    examples = "\n\n" + self.tr("msg_skipped", n=skipped)
                    if sample:
                        examples += "\n" + self.tr("msg_skipped_examples", items="\n".join(sample))

            full_msg = msg + examples
            self.status.showMessage(msg, 10000)
            QMessageBox.information(self, self.tr("msg_done_title"), full_msg)
            return

        if code == "cancelled":
            self.status.showMessage(self.tr("status_cancelled"), 8000)
            QMessageBox.information(self, self.tr("msg_cancel_title"), self.tr("msg_cancel_text"))
            return

        if code == "writer_open_failed":
            msg = self.tr("msg_writer_fail")
            self.status.showMessage(msg, 10000)
            QMessageBox.critical(self, self.tr("msg_error_title"), msg)
            return

        # generic error
        msg = self.tr("msg_generic_error", err=detail or code)
        self.status.showMessage(msg, 10000)
        QMessageBox.critical(self, self.tr("msg_error_title"), msg)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
