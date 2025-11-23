#!/usr/bin/env python3
"""
images_to_mp4.py

Source: github.com/zeittresor

Ein einfaches GUI-Tool (PyQt5) um beliebig viele Bilder per Drag & Drop
oder Dateiauswahl hinzuzufügen und daraus ein MP4-Video zu erstellen.

Benötigte Pakete:
    pip install PyQt5 Pillow opencv-python

Funktionen:
- Drag & Drop von Bildern in die Listenansicht
- Bilder per Dateidialog hinzufügen
- Reihenfolge änderbar (Drag within list)
- Einstellbar: Bildwechsel-Intervall in ms (default 40ms)
- Einstellbar: Ausgabegröße (default 512x512)
- Lanczos-Resampling beim Skalieren (Pillow Image.LANCZOS)
- Save-Dialog um MP4 zu speichern
- Fortschrittsanzeige
"""
import sys
import os
from PIL import Image
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLabel,
    QSpinBox, QProgressBar, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon

SUPPORTED_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

class ImageListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)  # allow reorder

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            paths = []
            for url in e.mimeData().urls():
                p = url.toLocalFile()
                if os.path.isdir(p):
                    # add all supported images in directory (non-recursive)
                    for fname in sorted(os.listdir(p)):
                        if fname.lower().endswith(SUPPORTED_EXTS):
                            paths.append(os.path.join(p, fname))
                elif p.lower().endswith(SUPPORTED_EXTS):
                    paths.append(p)
            if paths:
                self.parent().add_images(paths)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

class VideoWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, image_paths, out_path, width, height, interval_ms):
        super().__init__()
        self.image_paths = image_paths
        self.out_path = out_path
        self.width = width
        self.height = height
        self.interval_ms = interval_ms

    def run(self):
        try:
            if not self.image_paths:
                self.finished.emit(False, "Keine Bilder gewählt.")
                return

            fps = 1000.0 / max(1, self.interval_ms)  # frames per second
            # OpenCV requires frame size as (width, height)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(self.out_path, fourcc, fps, (self.width, self.height))

            total = len(self.image_paths)
            for idx, p in enumerate(self.image_paths):
                try:
                    img = Image.open(p).convert('RGBA')
                except Exception as e:
                    # skip bad image
                    print(f"Warnung: Konnte {p} nicht öffnen: {e}")
                    continue

                # Resize while preserving aspect ratio using Lanczos
                img_w, img_h = img.size
                target_w, target_h = self.width, self.height

                # compute scale while keeping aspect ratio
                scale = min(target_w / img_w, target_h / img_h)
                new_w = max(1, int(round(img_w * scale)))
                new_h = max(1, int(round(img_h * scale)))
                resized = img.resize((new_w, new_h), resample=Image.LANCZOS)

                # Paste centered on black background (preserving alpha if any)
                background = Image.new('RGB', (target_w, target_h), (0,0,0))
                paste_x = (target_w - new_w) // 2
                paste_y = (target_h - new_h) // 2
                # If image has alpha, composite on black first
                if resized.mode in ('RGBA', 'LA') or (resized.mode == 'P' and 'transparency' in resized.info):
                    background.paste(resized.convert('RGBA'), (paste_x, paste_y), resized.convert('RGBA'))
                else:
                    background.paste(resized.convert('RGB'), (paste_x, paste_y))

                # Convert to BGR for OpenCV
                frame = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
                writer.write(frame)

                progress_percent = int((idx + 1) / total * 100)
                self.progress.emit(progress_percent)

            writer.release()
            self.finished.emit(True, f"Video gespeichert: {self.out_path}")
        except Exception as e:
            self.finished.emit(False, f"Fehler: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilder → MP4 (Drag & Drop)")
        self.resize(700, 480)
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        central.setLayout(layout)

        # Image list
        self.list_widget = ImageListWidget(self)
        layout.addWidget(self.list_widget)

        # Controls row 1
        row1 = QHBoxLayout()
        btn_add = QPushButton("Dateien hinzufügen...")
        btn_add.clicked.connect(self.on_add_files)
        row1.addWidget(btn_add)

        btn_remove = QPushButton("Ausgewählte entfernen")
        btn_remove.clicked.connect(self.on_remove_selected)
        row1.addWidget(btn_remove)

        btn_clear = QPushButton("Liste leeren")
        btn_clear.clicked.connect(self.on_clear)
        row1.addWidget(btn_clear)

        layout.addLayout(row1)

        # Controls row 2
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Intervall (ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 10000)
        self.spin_interval.setValue(40)
        row2.addWidget(self.spin_interval)

        row2.addWidget(QLabel("Breite:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 8192)
        self.spin_width.setValue(512)
        row2.addWidget(self.spin_width)

        row2.addWidget(QLabel("Höhe:"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 8192)
        self.spin_height.setValue(512)
        row2.addWidget(self.spin_height)

        layout.addLayout(row2)

        # Controls row 3
        row3 = QHBoxLayout()
        btn_save = QPushButton("Zieldatei auswählen...")
        btn_save.clicked.connect(self.on_choose_save)
        row3.addWidget(btn_save)

        self.label_out = QLabel("Noch keine Zieldatei gewählt")
        row3.addWidget(self.label_out, 1)

        layout.addLayout(row3)

        # Controls row 4
        row4 = QHBoxLayout()
        self.btn_create = QPushButton("Video erstellen")
        self.btn_create.clicked.connect(self.on_create_video)
        row4.addWidget(self.btn_create)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        row4.addWidget(self.progress)

        layout.addLayout(row4)

        # Status
        self.status = self.statusBar()
        self.out_path = None
        self.worker = None

    def add_images(self, paths):
        for p in paths:
            item = QListWidgetItem(p)
            item.setToolTip(p)
            self.list_widget.addItem(item)

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Bilder wählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if files:
            self.add_images(files)

    def on_remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def on_clear(self):
        self.list_widget.clear()
        self.progress.setValue(0)

    def on_choose_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Speichern als", "output.mp4", "MP4 Video (*.mp4)")
        if path:
            if not path.lower().endswith('.mp4'):
                path += '.mp4'
            self.out_path = path
            self.label_out.setText(self.out_path)

    def on_create_video(self):
        if not self.out_path:
            QMessageBox.warning(self, "Keine Zieldatei", "Bitte wähle zuerst eine Zieldatei zum Speichern.")
            return
        image_paths = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if not image_paths:
            QMessageBox.warning(self, "Keine Bilder", "Bitte füge zuerst Bilder hinzu (Drag & Drop oder Dateien hinzufügen).")
            return

        width = int(self.spin_width.value())
        height = int(self.spin_height.value())
        interval_ms = int(self.spin_interval.value())

        self.btn_create.setEnabled(False)
        self.worker = VideoWorker(image_paths, self.out_path, width, height, interval_ms)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        self.status.showMessage("Erstelle Video...")

    def on_finished(self, ok, msg):
        self.btn_create.setEnabled(True)
        self.status.showMessage(msg, 10000)
        QMessageBox.information(self, "Fertig" if ok else "Fehler", msg)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
