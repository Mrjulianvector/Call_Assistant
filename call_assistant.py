#!/usr/bin/env python3
"""
Call Assistant - Audio Soundboard for Live Calls
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
from backend.audio_diagnostics import AudioDiagnostics
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


class CallAssistantApp(QMainWindow):
    """Main Call Assistant desktop application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Call Assistant - Audio Soundboard")
        self.setGeometry(100, 100, 1300, 850)
        
        # Apply modern theme with gradients
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1e2e, stop:1 #181825);
            }
            QWidget {
                background-color: transparent;
                color: #cdd6f4;
                font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
                font-size: 11pt;
            }
            QLabel {
                color: #cdd6f4;
                background-color: transparent;
            }
            QTabWidget::pane {
                border: 2px solid #45475a;
                background-color: #181825;
                border-radius: 12px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #a6adc8;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 11pt;
                font-weight: 600;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #89b4fa, stop:1 #74c7ec);
                color: #1e1e2e;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #89b4fa, stop:1 #74c7ec);
                color: #1e1e2e;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: 700;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b4befe, stop:1 #89dceb);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #74c7ec, stop:1 #89b4fa);
            }
            QSlider::groove:horizontal {
                background: #313244;
                height: 10px;
                border-radius: 5px;
                border: 1px solid #45475a;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #b4befe);
                width: 22px;
                height: 22px;
                margin: -7px 0;
                border-radius: 11px;
                border: 2px solid #1e1e2e;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b4befe, stop:1 #cba6f7);
                width: 24px;
                height: 24px;
                margin: -8px 0;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #74c7ec);
                border-radius: 5px;
            }
            QComboBox, QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 2px solid #45475a;
                padding: 10px 15px;
                border-radius: 8px;
                font-size: 11pt;
                min-height: 20px;
            }
            QComboBox:hover, QLineEdit:hover {
                border: 2px solid #89b4fa;
                background-color: #3d3f54;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 2px solid #74c7ec;
                background-color: #3d3f54;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 10px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 6px;
                margin: 3px;
                background-color: #313244;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #74c7ec);
                color: #1e1e2e;
                font-weight: 600;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #181825;
                width: 14px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #45475a, stop:1 #585b70);
                border-radius: 7px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #585b70, stop:1 #6c7086);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Initialize audio controller
        self.controller = AppController()

        # Start the application (audio mixer + hotkey listener)
        if self.controller.start():
            logger.info("Application started successfully")
        else:
            logger.warning("Failed to start application")

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
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("🎵 Call Assistant - Audio Soundboard")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #89b4fa;")
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
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header with import button and stop all
        header_layout = QHBoxLayout()
        
        title = QLabel("🎵 Your Audio Clips")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #b4befe;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        import_btn = QPushButton("📁 Import Clip")
        import_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #a6e3a1, stop:1 #94e2d5);
                color: #1e1e2e;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b8f0b8, stop:1 #a9f0e5);
            }
        """)
        import_btn.clicked.connect(self.import_clip)
        header_layout.addWidget(import_btn)

        stop_all_btn = QPushButton("⏹️ Stop All")
        stop_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f38ba8, stop:1 #eba0ac);
                color: #1e1e2e;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffa0b8, stop:1 #ffb0bc);
            }
        """)
        stop_all_btn.clicked.connect(self.stop_all)
        header_layout.addWidget(stop_all_btn)

        layout.addLayout(header_layout)

        # Scrollable area for clip cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Container for cards
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #313244, stop:1 #292939);
                border: 2px solid #45475a;
                border-radius: 12px;
                padding: 15px;
            }
            QFrame:hover {
                border: 2px solid #89b4fa;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3d54, stop:1 #323349);
            }
        """)
        card.setMinimumHeight(160)
        card.setMaximumHeight(190)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(10)

        # Clip name
        name_label = QLabel(f"🎵 {clip_name}")
        name_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        name_label.setFont(name_font)
        name_label.setStyleSheet("""
            color: #ffffff;
            background: transparent;
            padding: 10px;
            font-size: 16px;
        """)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(name_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #45475a;")
        separator.setMaximumHeight(1)
        card_layout.addWidget(separator)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        play_btn = QPushButton("▶️ Play")
        play_btn.clicked.connect(lambda: self.controller.play_clip(clip_id))
        play_btn.setMinimumHeight(55)
        play_btn.setMinimumWidth(80)
        play_btn.setMaximumWidth(100)
        play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #a6e3a1, stop:1 #94e2d5);
                color: #1e1e2e;
                border-radius: 8px;
                font-weight: 700;
                padding: 8px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b8f0b8, stop:1 #a9f0e5);
            }
        """)
        buttons_layout.addWidget(play_btn)

        stop_btn = QPushButton("⏸️ Stop")
        stop_btn.clicked.connect(lambda: self.controller.stop_clip(clip_id))
        stop_btn.setMinimumHeight(55)
        stop_btn.setMinimumWidth(80)
        stop_btn.setMaximumWidth(100)
        stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fab387, stop:1 #f9e2af);
                color: #1e1e2e;
                border-radius: 8px;
                font-weight: 700;
                padding: 8px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffc397, stop:1 #fff2bf);
            }
        """)
        buttons_layout.addWidget(stop_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(lambda: self.delete_clip_from_card(clip_id, clip_name))
        delete_btn.setMinimumHeight(55)
        delete_btn.setMinimumWidth(65)
        delete_btn.setMaximumWidth(120)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f38ba8, stop:1 #eba0ac);
                color: #1e1e2e;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: 700;
                padding: 8px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffa0b8, stop:1 #ffb0bc);
            }
        """)
        buttons_layout.addWidget(delete_btn)

        card_layout.addLayout(buttons_layout)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(25)

        # Title
        title = QLabel("🎛️ Volume Controls")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #b4befe;")
        layout.addWidget(title)

        # Master Volume
        layout.addWidget(QLabel("🔊 Master Volume:"))
        master_layout = QHBoxLayout()
        self.master_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_volume_slider.setMinimum(0)
        self.master_volume_slider.setMaximum(100)
        self.master_volume_slider.setValue(100)
        self.master_volume_slider.valueChanged.connect(self.set_master_volume)
        master_layout.addWidget(self.master_volume_slider)
        self.master_volume_label = QLabel("100%")
        self.master_volume_label.setStyleSheet("color: #89b4fa; font-weight: bold; min-width: 50px;")
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
        self.mic_volume_label.setStyleSheet("color: #89b4fa; font-weight: bold; min-width: 50px;")
        mic_layout.addWidget(self.mic_volume_label)
        layout.addLayout(mic_layout)

        # Clips Volume
        layout.addWidget(QLabel("🎵 Clips Volume:"))
        clips_layout = QHBoxLayout()
        self.clips_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.clips_volume_slider.setMinimum(0)
        self.clips_volume_slider.setMaximum(100)
        self.clips_volume_slider.setValue(90)
        self.clips_volume_slider.valueChanged.connect(self.set_clips_volume)
        clips_layout.addWidget(self.clips_volume_slider)
        self.clips_volume_label = QLabel("90%")
        self.clips_volume_label.setStyleSheet("color: #89b4fa; font-weight: bold; min-width: 50px;")
        clips_layout.addWidget(self.clips_volume_label)
        layout.addLayout(clips_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_hotkeys_tab(self):
        """Create the hotkeys tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("⌨️ Keyboard Shortcuts")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #b4befe;")
        layout.addWidget(title)

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
        remove_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f38ba8, stop:1 #eba0ac);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffa0b8, stop:1 #ffb0bc);
            }
        """)
        remove_btn.clicked.connect(self.remove_hotkey)
        layout.addWidget(remove_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_settings_tab(self):
        """Create the settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("⚙️ Audio Device Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #b4befe;")
        layout.addWidget(title)

        # Run diagnostics button
        diag_button = QPushButton("🔍 Run Audio Diagnostics")
        diag_button.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: 2px solid #585b70;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #585b70;
                border: 2px solid #74c7ec;
            }
        """)
        diag_button.clicked.connect(self.run_diagnostics)
        layout.addWidget(diag_button)

        # Diagnostics output area
        self.diag_output = QLabel()
        self.diag_output.setWordWrap(True)
        self.diag_output.setStyleSheet("color: #94e2d5; background-color: #1e1e2e; padding: 12px; border-radius: 8px; font-family: 'Courier New';")
        layout.addWidget(self.diag_output)

        # Device selection section
        layout.addWidget(QLabel(""))  # Spacer

        device_title = QLabel("📡 Device Configuration")
        device_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        device_title.setStyleSheet("color: #b4befe;")
        layout.addWidget(device_title)

        # Input device selector
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Microphone Input:"))
        self.input_device_combo = QComboBox()
        self.input_device_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 8px;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #45475a;
            }
        """)
        self.input_device_combo.currentTextChanged.connect(self.on_input_device_changed)
        input_layout.addWidget(self.input_device_combo)
        layout.addLayout(input_layout)

        # Output device selector
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Speaker Output:"))
        self.output_device_combo = QComboBox()
        self.output_device_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 8px;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #45475a;
            }
        """)
        self.output_device_combo.currentTextChanged.connect(self.on_output_device_changed)
        output_layout.addWidget(self.output_device_combo)
        layout.addLayout(output_layout)

        # Recommendations section
        rec_title = QLabel("💡 Recommendations")
        rec_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        rec_title.setStyleSheet("color: #b4befe;")
        layout.addWidget(rec_title)

        self.recommendations_label = QLabel()
        self.recommendations_label.setWordWrap(True)
        self.recommendations_label.setStyleSheet("color: #f38ba8; background-color: #1e1e2e; padding: 12px; border-radius: 8px;")
        layout.addWidget(self.recommendations_label)

        # Info section
        info_title = QLabel("ℹ️ Information")
        info_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        info_title.setStyleSheet("color: #b4befe;")
        layout.addWidget(info_title)

        self.info_label = QLabel("📦 Version: 1.0.0\n🎵 Sample Rate: 48kHz\n⚡ Status: Ready")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #89b4fa; background-color: #1e1e2e; padding: 12px; border-radius: 8px;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Load device list on startup
        self.refresh_device_list()

        widget.setLayout(layout)
        return widget

    def refresh_device_list(self):
        """Refresh the list of audio devices"""
        try:
            diag = AudioDiagnostics()
            report = diag.diagnose()

            # Populate input devices
            self.input_device_combo.blockSignals(True)
            self.input_device_combo.clear()
            for device in report['input_devices']:
                self.input_device_combo.addItem(f"{device.name}", device.index)
            if report['microphone']:
                self.input_device_combo.setCurrentText(report['microphone'].name)
            self.input_device_combo.blockSignals(False)

            # Populate output devices
            self.output_device_combo.blockSignals(True)
            self.output_device_combo.clear()
            for device in report['output_devices']:
                self.output_device_combo.addItem(f"{device.name}", device.index)
            if report['vbcable']:
                self.output_device_combo.setCurrentText(report['vbcable'].name)
            self.output_device_combo.blockSignals(False)

            diag.cleanup()
        except Exception as e:
            logger.error(f"Error refreshing device list: {e}")

    def run_diagnostics(self):
        """Run full audio diagnostics and display report"""
        try:
            diag = AudioDiagnostics()
            report = diag.diagnose()

            # Build diagnostics output
            output = "AUDIO DEVICE DIAGNOSTICS\n"
            output += "=" * 40 + "\n\n"

            output += "ALL DEVICES:\n"
            for device in report['all_devices']:
                io_info = f"In:{device.max_input_channels} Out:{device.max_output_channels}"
                output += f"  Device {device.index}: {device.name}\n    ({io_info}, {device.sample_rate}Hz)\n"

            output += "\nDETECTED:\n"
            if report['vbcable']:
                output += f"  ✓ VB-Cable: {report['vbcable'].name}\n"
            else:
                output += "  ✗ VB-Cable: NOT FOUND\n"

            if report['microphone']:
                output += f"  ✓ Microphone: {report['microphone'].name}\n"
            else:
                output += "  ✗ Microphone: NOT FOUND\n"

            if report['builtin_speakers']:
                output += f"  ✓ Speakers: {report['builtin_speakers'].name}\n"
            else:
                output += "  ✗ Speakers: NOT FOUND\n"

            self.diag_output.setText(output)

            # Build recommendations
            recommendations = []
            if not report['microphone']:
                recommendations.append("⚠️ No dedicated microphone found. Connect a USB microphone or enable your system microphone.")

            if report['default_input'] and "vb-cable" in report['default_input'].name.lower():
                recommendations.append("⚠️ Default input is VB-Cable. Your microphone should be the input device, not VB-Cable.")

            if not report['builtin_speakers'] or ("hdmi" in report['builtin_speakers'].name.lower()):
                recommendations.append("⚠️ Wrong speaker output detected. Use Mac mini Speakers, not HDMI output.")

            if not recommendations:
                recommendations.append("✓ All audio devices appear to be configured correctly!")

            self.recommendations_label.setText("\n".join(recommendations))

            diag.cleanup()

            QMessageBox.information(self, "Diagnostics Complete", "Audio diagnostics completed. See the output above.")
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}")
            QMessageBox.critical(self, "Error", f"Failed to run diagnostics: {str(e)}")

    def on_input_device_changed(self, device_name):
        """Handle input device selection change"""
        if device_name and self.sender() == self.input_device_combo:
            device_index = self.input_device_combo.currentData()
            logger.info(f"Selected input device: {device_name} (Index: {device_index})")
            # Note: Actual device switching would require audio engine restart

    def on_output_device_changed(self, device_name):
        """Handle output device selection change"""
        if device_name and self.sender() == self.output_device_combo:
            device_index = self.output_device_combo.currentData()
            logger.info(f"Selected output device: {device_name} (Index: {device_index})")
            # Note: Actual device switching would require audio engine restart

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
                QMessageBox.information(self, "Success", f"✅ Imported '{clip_name}'")
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

            # Create cards for each clip (3 columns)
            row = 0
            col = 0
            for clip_id, clip in self.controller.audio_mixer.clips.items():
                card = self.create_clip_card(clip_id, clip.name)
                self.cards_layout.addWidget(card, row, col)

                col += 1
                if col >= 3:  # Changed from 2 to 3 columns
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

        if len(hotkey) < 2:
            QMessageBox.warning(self, "Warning", "Hotkey must be at least 2 characters (e.g., 'F1', 'ctrl+p')")
            return

        valid_chars = set("abcdefghijklmnopqrstuvwxyz0123456789+-_* f")
        if not all(c.lower() in valid_chars for c in hotkey):
            QMessageBox.warning(self, "Warning", "Hotkey contains invalid characters. Use format like 'ctrl+alt+p' or 'F1'")
            return

        try:
            if self.controller.assign_hotkey(clip_id, hotkey):
                QMessageBox.information(self, "Success", f"✅ Assigned hotkey '{hotkey}'")
                self.hotkey_input.clear()
                self.refresh_hotkeys_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to assign hotkey")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to assign hotkey: {str(e)}")

    def remove_hotkey(self):
        """Remove the selected hotkey"""
        current_item = self.hotkeys_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a hotkey to remove")
            return

        hotkey_text = current_item.text()
        parts = hotkey_text.split(": ")
        if len(parts) < 2:
            return

        hotkey = parts[1]
        hotkey_mapping = self.controller.clip_manager.get_hotkey_mapping()
        clip_id = hotkey_mapping.get(hotkey)

        if not clip_id:
            QMessageBox.warning(self, "Error", "Could not find clip for this hotkey")
            return

        try:
            self.controller.unassign_hotkey(clip_id, hotkey)
            QMessageBox.information(self, "Success", f"✅ Removed hotkey '{hotkey}'")
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
            if hasattr(self, 'info_label'):
                self.info_label.setText(
                    f"📦 Version: 1.0.0\n"
                    f"🎵 Sample Rate: 48kHz\n"
                    f"⚡ Clips Loaded: {status['clips_loaded']}\n"
                    f"🔊 Master: {int(status['master_volume']*100)}% | "
                    f"🎤 Mic: {int(status['mic_volume']*100)}% | "
                    f"🎹 Clips: {int(status['clip_volume']*100)}%"
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
    window = CallAssistantApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()