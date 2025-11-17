"""
Hotkey Manager - Global hotkey detection and handling
Works even when the app is minimized or in the background
"""

from pynput import keyboard
from typing import Callable, Dict, Optional
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HotkeyManager:
    """
    Manages global hotkey registration and triggering
    Uses pynput for system-wide hotkey detection
    """

    def __init__(self, on_hotkey_pressed: Optional[Callable] = None):
        """
        Initialize hotkey manager

        Args:
            on_hotkey_pressed: Callback function(hotkey_id, hotkey_string)
        """
        self.on_hotkey_pressed = on_hotkey_pressed
        self.hotkey_handlers: Dict[str, Callable] = {}
        self.listener = None
        self.is_listening = False

        # Track currently pressed keys for combo detection
        self.pressed_keys = set()

    def start_listening(self) -> bool:
        """Start listening for global hotkeys"""
        if self.is_listening:
            logger.warning("Already listening for hotkeys")
            return False

        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)
            self.listener.start()
            self.is_listening = True
            logger.info("Hotkey listener started")
            return True

        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}")
            return False

    def stop_listening(self) -> bool:
        """Stop listening for global hotkeys"""
        if not self.is_listening:
            return False

        try:
            if self.listener:
                self.listener.stop()
            self.is_listening = False
            logger.info("Hotkey listener stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping hotkey listener: {e}")
            return False

    def register_hotkey(self, hotkey_string: str, callback: Callable) -> bool:
        """
        Register a hotkey with a callback

        Args:
            hotkey_string: Hotkey string (e.g., "ctrl+alt+p", "F1", "ctrl+shift+m")
            callback: Function to call when hotkey is pressed

        Returns:
            True if successfully registered
        """
        if not hotkey_string:
            logger.warning("Invalid hotkey string")
            return False

        try:
            self.hotkey_handlers[hotkey_string.lower()] = callback
            logger.info(f"Hotkey registered: {hotkey_string}")
            return True

        except Exception as e:
            logger.error(f"Error registering hotkey: {e}")
            return False

    def unregister_hotkey(self, hotkey_string: str) -> bool:
        """Unregister a hotkey"""
        hotkey_lower = hotkey_string.lower()
        if hotkey_lower in self.hotkey_handlers:
            del self.hotkey_handlers[hotkey_lower]
            logger.info(f"Hotkey unregistered: {hotkey_string}")
            return True
        return False

    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            # Get key representation
            try:
                key_char = key.char
            except AttributeError:
                key_char = key.name

            # Add to pressed keys
            if key_char:
                self.pressed_keys.add(key_char.lower())

            # Check all registered hotkeys
            for hotkey_string, callback in self.hotkey_handlers.items():
                if self._check_hotkey_match(hotkey_string):
                    try:
                        callback()
                        logger.info(f"Hotkey triggered: {hotkey_string}")

                        if self.on_hotkey_pressed:
                            self.on_hotkey_pressed(hotkey_string)

                    except Exception as e:
                        logger.error(f"Error in hotkey callback: {e}")

        except Exception as e:
            logger.error(f"Error in key press handler: {e}")

    def _on_key_release(self, key):
        """Handle key release events"""
        try:
            try:
                key_char = key.char
            except AttributeError:
                key_char = key.name

            if key_char:
                self.pressed_keys.discard(key_char.lower())

        except Exception as e:
            logger.error(f"Error in key release handler: {e}")

    def _check_hotkey_match(self, hotkey_string: str) -> bool:
        """
        Check if a hotkey combination is currently pressed

        Args:
            hotkey_string: Hotkey string like "ctrl+alt+p" or "F1"

        Returns:
            True if hotkey is matched
        """
        hotkey_lower = hotkey_string.lower()

        # Simple hotkey pattern: modifier1+modifier2+key
        parts = hotkey_lower.split("+")

        required_modifiers = set()
        required_key = None

        for part in parts:
            part = part.strip()
            if part in ["ctrl", "control"]:
                required_modifiers.add("ctrl")
            elif part in ["alt"]:
                required_modifiers.add("alt")
            elif part in ["shift"]:
                required_modifiers.add("shift")
            elif part in ["cmd", "command", "super"]:
                required_modifiers.add("cmd")
            else:
                required_key = part

        # Check if modifiers are pressed
        if "ctrl" in required_modifiers and "ctrl" not in self.pressed_keys:
            return False
        if "alt" in required_modifiers and "alt" not in self.pressed_keys:
            return False
        if "shift" in required_modifiers and "shift" not in self.pressed_keys:
            return False
        if "cmd" in required_modifiers and "cmd" not in self.pressed_keys:
            return False

        # Check if main key is pressed
        if required_key and required_key not in self.pressed_keys:
            return False

        return True

    def get_registered_hotkeys(self) -> Dict[str, str]:
        """Get all registered hotkeys"""
        return self.hotkey_handlers.copy()

    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        self.hotkey_handlers.clear()
        logger.info("Hotkey manager cleaned up")
