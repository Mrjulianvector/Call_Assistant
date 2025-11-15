#!/usr/bin/env python3
"""
Talkless Desktop Audio Soundboard
Pure Python GUI using PyQt6 + PyAudio
"""

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QGridLayout, QFileDialog, QTabWidget,
    QListWidget, QListWidgetItem, QDialog, QInputDialog, QMessageBox,
    QProgressBar, QComboBox, QLineEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QFont, QColor

from backend.app_controller import AppController
from backend.audio_engine import AudioClip
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioWorkerThread(QThread):
    """Background thread for audio operations"""
    status_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.is_running = True

    def run(self):
        """Run status updates in background"""
        while self.is_running:
            try:
                status = {
                    'clips_loaded': len(self.controller.audio_mixer.clips),
                    'master_volume': self.controller.audio_mixer.master_volume,
                    'mic_volume': self.controller.audio_mixer.mic_volume,
                    'clip_volume': self.controller.audio_mixer.clip_volume,
                    'is_running': self.controller.audio_mixer.is_running,
                }
                self.status_updated.emit(status)
            except Exception as e:
                self.error_occurred.emit(str(e))
            self.msleep(500)

    def stop(self):
        """Stop the worker thread"""
        self.is_running = False
        self.wait()


class TalklessApp(QMainWindow):
    """Main Talkless desktop application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Talkless - Audio Soundboard")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize audio controller
        self.controller = AppController()

        # Start audio mixer
        if self.controller.audio_mixer.start():
            logger.info("Audio mixer started successfully")
        else:
            logger.warning("Failed to start audio mixer")

        # Worker thread for status updates
        self.worker = AudioWorkerThread(self.controller)
        self.worker.status_updated.connect(self.update_status)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.start()

        # Create UI
        self.init_ui()

        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_clips)
        self.update_timer.start(1000)

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # Header
        header = QLabel("🎵 Talkless Audio Soundboard")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        main_layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self.create_soundboard_tab(), "🎹 Soundboard")
        tabs.addTab(self.create_controls_tab(), "🎛️ Controls")
        tabs.addTab(self.create_hotkeys_tab(), "⌨️ Hotkeys")
        tabs.addTab(self.create_settings_tab(), "⚙️ Settings")
        main_layout.addWidget(tabs)

        central_widget.setLayout(main_layout)

    def create_soundboard_tab(self):
        """Create the soundboard tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Header with import button and stop all
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("🎵 Your Audio Clips"))
        header_layout.addStretch()

        import_btn = QPushButton("📁 Import Clip")
        import_btn.clicked.connect(self.import_clip)
        header_layout.addWidget(import_btn)

        stop_all_btn = QPushButton("⏹️ Stop All")
        stop_all_btn.clicked.connect(self.stop_all)
        header_layout.addWidget(stop_all_btn)

        layout.addLayout(header_layout)

        # Scrollable area for clip cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Container for cards
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(10)
        self.cards_container.setLayout(self.cards_layout)

        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)

        widget.setLayout(layout)
        return widget

    def create_clip_card(self, clip_id, clip_name):
        """Create a card widget for a clip"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #444444;
                border-radius: 6px;
                background-color: #2d2d2d;
                padding: 8px;
            }
            QFrame:hover {
                border: 2px solid #0078d4;
                background-color: #3a3a3a;
            }
        """)
        card.setMaximumHeight(100)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(6)

        # Clip name (white text, better visibility)
        name_label = QLabel(f"🎵 {clip_name}")
        name_font = QFont()
        name_font.setPointSize(10)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #ffffff; background-color: transparent;")
        name_label.setMaximumHeight(24)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(name_label)

        # Buttons layout (compact)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        play_btn = QPushButton("▶️")
        play_btn.clicked.connect(lambda: self.controller.play_clip(clip_id))
        play_btn.setMaximumWidth(42)
        play_btn.setMaximumHeight(30)
        play_btn.setToolTip("Play")
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0078d4;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        buttons_layout.addWidget(play_btn)

        stop_btn = QPushButton("⏸️")
        stop_btn.clicked.connect(lambda: self.controller.stop_clip(clip_id))
        stop_btn.setMaximumWidth(42)
        stop_btn.setMaximumHeight(30)
        stop_btn.setToolTip("Stop")
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d46d0c;
            }
            QPushButton:pressed {
                background-color: #a85509;
            }
        """)
        buttons_layout.addWidget(stop_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.clicked.connect(lambda: self.delete_clip_from_card(clip_id, clip_name))
        delete_btn.setMaximumWidth(42)
        delete_btn.setMaximumHeight(30)
        delete_btn.setToolTip("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c41e3a;
            }
            QPushButton:pressed {
                background-color: #8b1528;
            }
        """)
        buttons_layout.addWidget(delete_btn)

        buttons_layout.addStretch()
        card_layout.addLayout(buttons_layout)
        card_layout.addStretch()

        card.setLayout(card_layout)
        return card

    def delete_clip_from_card(self, clip_id, clip_name):
        """Delete a clip from the card interface"""
        reply = QMessageBox.question(
            self,
            "Delete Clip",
            f"Are you sure you want to delete '{clip_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.controller.delete_clip(clip_id)
                self.refresh_clips()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

    def create_controls_tab(self):
        """Create the controls tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Master Volume
        layout.addWidget(QLabel("Master Volume:"))
        master_layout = QHBoxLayout()
        self.master_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_volume_slider.setMinimum(0)
        self.master_volume_slider.setMaximum(100)
        self.master_volume_slider.setValue(100)
        self.master_volume_slider.valueChanged.connect(self.set_master_volume)
        master_layout.addWidget(self.master_volume_slider)
        self.master_volume_label = QLabel("100%")
        master_layout.addWidget(self.master_volume_label)
        layout.addLayout(master_layout)

        # Microphone Volume
        layout.addWidget(QLabel("🎙️ Microphone Volume:"))
        mic_layout = QHBoxLayout()
        self.mic_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.mic_volume_slider.setMinimum(0)
        self.mic_volume_slider.setMaximum(100)
        self.mic_volume_slider.setValue(100)
        self.mic_volume_slider.valueChanged.connect(self.set_mic_volume)
        mic_layout.addWidget(self.mic_volume_slider)
        self.mic_volume_label = QLabel("100%")
        mic_layout.addWidget(self.mic_volume_label)
        layout.addLayout(mic_layout)

        # Clips Volume
        layout.addWidget(QLabel("Clips Volume:"))
        clips_layout = QHBoxLayout()
        self.clips_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.clips_volume_slider.setMinimum(0)
        self.clips_volume_slider.setMaximum(100)
        self.clips_volume_slider.setValue(90)
        self.clips_volume_slider.valueChanged.connect(self.set_clips_volume)
        clips_layout.addWidget(self.clips_volume_slider)
        self.clips_volume_label = QLabel("90%")
        clips_layout.addWidget(self.clips_volume_label)
        layout.addLayout(clips_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_hotkeys_tab(self):
        """Create the hotkeys tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("⌨️ Assign Hotkeys to Clips"))

        # Clips selection
        layout.addWidget(QLabel("Select Clip:"))
        self.hotkey_clips_combo = QComboBox()
        layout.addWidget(self.hotkey_clips_combo)

        # Hotkey input
        layout.addWidget(QLabel("Hotkey (e.g., ctrl+alt+1):"))
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("Press keys or type hotkey")
        layout.addWidget(self.hotkey_input)

        # Assign button
        assign_btn = QPushButton("🔑 Assign Hotkey")
        assign_btn.clicked.connect(self.assign_hotkey)
        layout.addWidget(assign_btn)

        # Hotkeys list
        layout.addWidget(QLabel("Assigned Hotkeys:"))
        self.hotkeys_list = QListWidget()
        layout.addWidget(self.hotkeys_list)

        # Remove hotkey button
        remove_btn = QPushButton("❌ Remove Selected Hotkey")
        remove_btn.clicked.connect(self.remove_hotkey)
        layout.addWidget(remove_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_settings_tab(self):
        """Create the settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("⚙️ Settings"))
        layout.addWidget(QLabel("Version: 0.1.0"))
        layout.addWidget(QLabel("Status: Ready"))

        # Status info
        self.status_label = QLabel("Loading...")
        layout.addWidget(self.status_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def import_clip(self):
        """Import an audio clip"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Import Audio Clip",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac);;All Files (*)"
        )

        if not file_path:
            return

        # Get clip name
        clip_name, ok = QInputDialog.getText(
            self,
            "Clip Name",
            "Enter a name for this clip:",
            text=Path(file_path).stem
        )

        if ok and clip_name:
            try:
                self.controller.import_audio_file(file_path, clip_name)
                self.refresh_clips()
                QMessageBox.information(self, "Success", f"Imported '{clip_name}'")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")


    def refresh_clips(self):
        """Refresh the clips cards"""
        try:
            # Clear existing cards
            while self.cards_layout.count():
                item = self.cards_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.hotkey_clips_combo.clear()

            # Create cards for each clip (2 columns for compact view)
            row = 0
            col = 0
            for clip_id, clip in self.controller.audio_mixer.clips.items():
                card = self.create_clip_card(clip_id, clip.name)
                self.cards_layout.addWidget(card, row, col)

                col += 1
                if col >= 2:
                    col = 0
                    row += 1

                # Add to hotkey combo box
                self.hotkey_clips_combo.addItem(clip.name, clip_id)

            # Refresh hotkeys list
            self.refresh_hotkeys_list()
        except Exception as e:
            logger.error(f"Error refreshing clips: {e}")

    def stop_all(self):
        """Stop all playing clips"""
        try:
            self.controller.audio_mixer.stop_all_clips()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop: {str(e)}")

    def set_master_volume(self, value):
        """Set master volume"""
        try:
            self.controller.audio_mixer.set_master_volume(value / 100)
            self.master_volume_label.setText(f"{value}%")
        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    def set_mic_volume(self, value):
        """Set microphone volume"""
        try:
            self.controller.audio_mixer.set_mic_volume(value / 100)
            self.mic_volume_label.setText(f"{value}%")
        except Exception as e:
            logger.error(f"Error setting mic volume: {e}")

    def set_clips_volume(self, value):
        """Set clips volume"""
        try:
            self.controller.audio_mixer.set_clip_volume_global(value / 100)
            self.clips_volume_label.setText(f"{value}%")
        except Exception as e:
            logger.error(f"Error setting clips volume: {e}")

    def assign_hotkey(self):
        """Assign a hotkey to the selected clip"""
        if self.hotkey_clips_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "No clips available")
            return

        clip_id = self.hotkey_clips_combo.currentData()
        hotkey = self.hotkey_input.text().strip()

        if not hotkey:
            QMessageBox.warning(self, "Warning", "Please enter a hotkey")
            return

        try:
            self.controller.assign_hotkey(clip_id, hotkey)
            QMessageBox.information(self, "Success", f"Assigned hotkey '{hotkey}' to clip")
            self.hotkey_input.clear()
            self.refresh_hotkeys_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to assign hotkey: {str(e)}")

    def remove_hotkey(self):
        """Remove the selected hotkey"""
        current_item = self.hotkeys_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a hotkey to remove")
            return

        hotkey_text = current_item.text()
        # Extract hotkey from display text (format: "Clip Name: hotkey")
        parts = hotkey_text.split(": ")
        if len(parts) < 2:
            return

        hotkey = parts[1]
        # Find clip_id for this hotkey
        hotkey_mapping = self.controller.clip_manager.get_hotkey_mapping()
        clip_id = hotkey_mapping.get(hotkey)

        if not clip_id:
            QMessageBox.warning(self, "Error", "Could not find clip for this hotkey")
            return

        try:
            self.controller.unassign_hotkey(clip_id, hotkey)
            QMessageBox.information(self, "Success", f"Removed hotkey '{hotkey}'")
            self.refresh_hotkeys_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove hotkey: {str(e)}")

    def refresh_hotkeys_list(self):
        """Refresh the list of assigned hotkeys"""
        try:
            self.hotkeys_list.clear()
            hotkey_mapping = self.controller.clip_manager.get_hotkey_mapping()

            for hotkey, clip_id in hotkey_mapping.items():
                clip = self.controller.audio_mixer.clips.get(clip_id)
                if clip:
                    item = QListWidgetItem(f"{clip.name}: {hotkey}")
                    item.setData(Qt.ItemDataRole.UserRole, hotkey)
                    self.hotkeys_list.addItem(item)
        except Exception as e:
            logger.error(f"Error refreshing hotkeys list: {e}")

    def update_status(self, status):
        """Update status display"""
        try:
            self.status_label.setText(
                f"Clips: {status['clips_loaded']} | "
                f"Master: {int(status['master_volume']*100)}% | "
                f"Mic: {int(status['mic_volume']*100)}% | "
                f"Clips: {int(status['clip_volume']*100)}%"
            )
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def show_error(self, error):
        """Show error message"""
        logger.error(f"Worker error: {error}")

    def closeEvent(self, event):
        """Handle application close"""
        self.worker.stop()
        self.update_timer.stop()
        self.controller.audio_mixer.stop_all_clips()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = TalklessApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
