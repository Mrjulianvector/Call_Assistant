#!/usr/bin/env python3
"""
Test hotkey detection on macOS
Run this to see what keys pynput detects when you press them
"""

import logging
from backend.hotkey_manager import HotkeyManager
from pynput import keyboard

# Enable debug logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_hotkey_callback():
    """Callback when F1 is pressed"""
    logger.info("✅✅✅ F1 HOTKEY TRIGGERED! ✅✅✅")

def test_raw_listener():
    """Test raw pynput listener to see what keys are detected"""
    print("\n=== RAW KEY DETECTION TEST ===")
    print("Press F1 to see raw detection")
    print("Press Ctrl+C to exit\n")

    def on_press(key):
        try:
            print(f"RAW PRESS - char: {getattr(key, 'char', 'N/A')}, name: {getattr(key, 'name', 'N/A')}")
        except Exception as e:
            print(f"Error: {e}")

    def on_release(key):
        if key == keyboard.Key.esc:
            return False

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

def main():
    print("\n=== Testing Hotkey Detection ===")
    print("Press Cmd+Shift+P to trigger the hotkey")
    print("Press Ctrl+C to exit\n")

    # Create hotkey manager
    manager = HotkeyManager()

    # Register cmd+shift+p hotkey (F1 doesn't work on macOS)
    manager.register_hotkey("cmd+shift+p", test_hotkey_callback)
    logger.info("Registered Cmd+Shift+P hotkey")

    # Start listening
    if manager.start_listening():
        logger.info("Hotkey listener started - ready to test!")
        try:
            # Keep the listener running
            import time
            while True:
                time.sleep(0.1)
                # Print current pressed keys for debugging
                if manager.pressed_keys:
                    logger.debug(f"Currently pressed keys: {manager.pressed_keys}")
        except KeyboardInterrupt:
            logger.info("\nExiting...")
    else:
        logger.error("Failed to start hotkey listener")

    manager.cleanup()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "raw":
        test_raw_listener()
    else:
        main()
