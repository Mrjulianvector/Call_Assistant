"""
Talkless - Audio Soundboard for Calls
Backend package
"""

__version__ = "0.1.0"
__author__ = "Talkless Team"

from .audio_engine import AudioMixer, AudioClip
from .clip_manager import ClipManager
from .hotkey_manager import HotkeyManager
from .app_controller import AppController

__all__ = ["AudioMixer", "AudioClip", "ClipManager", "HotkeyManager", "AppController"]
