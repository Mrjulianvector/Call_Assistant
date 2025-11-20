"""
App Controller - Main application orchestrator
Coordinates between UI, audio engine, clip manager, and hotkey system
"""

import logging
from typing import Optional, Callable, Dict
from pathlib import Path
from .audio_engine import AudioMixer, AudioClip
from .clip_manager import ClipManager
from .hotkey_manager import HotkeyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppController:
    """Main application controller"""

    def __init__(self, status_callback: Optional[Callable] = None):
        """
        Initialize app controller

        Args:
            status_callback: Optional callback for status updates
        """
        self.status_callback = status_callback

        # Initialize subsystems
        self.audio_mixer = AudioMixer(status_callback=self._audio_status_callback)
        self.clip_manager = ClipManager()
        self.hotkey_manager = HotkeyManager(on_hotkey_pressed=self._on_hotkey_pressed)

        # Load existing clips into mixer
        self._load_clips_into_mixer()

        # State
        self.is_running = False

        logger.info("App Controller initialized")

    def start(self) -> bool:
        """Start the application"""
        if self.is_running:
            logger.warning("Application already running")
            return False

        try:
            # Start audio mixer
            if not self.audio_mixer.start():
                logger.error("Failed to start audio mixer")
                return False

            # Start hotkey listening
            if not self.hotkey_manager.start_listening():
                logger.warning("Failed to start hotkey listener")
                # Continue anyway - app can work without hotkeys

            # Setup hotkeys
            self._setup_hotkeys()

            self.is_running = True
            logger.info("Application started")
            self._update_status("app_started")
            return True

        except Exception as e:
            logger.error(f"Error starting application: {e}")
            self._update_status(f"error: {e}")
            return False

    def stop(self) -> bool:
        """Stop the application"""
        if not self.is_running:
            return False

        try:
            # Stop audio mixer
            self.audio_mixer.stop()

            # Stop hotkey listening
            self.hotkey_manager.stop_listening()

            self.is_running = False
            logger.info("Application stopped")
            self._update_status("app_stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping application: {e}")
            return False

    def import_audio_file(self, file_path: str, clip_name: Optional[str] = None) -> bool:
        """
        Import an audio file

        Args:
            file_path: Path to audio file
            clip_name: Optional custom name for the clip

        Returns:
            True if import successful
        """
        if not self.clip_manager.import_clip(file_path, clip_name):
            return False

        # Load into mixer
        clip_id = clip_name or Path(file_path).stem
        metadata = self.clip_manager.get_clip_metadata(clip_id)

        if metadata:
            clip = self.audio_mixer.clips.get(clip_id)
            if not clip:
                # Load the clip if not already in mixer
                loaded_clip = self.clip_manager.load_audio_file(metadata.path)
                if loaded_clip:
                    self.audio_mixer.add_clip(loaded_clip)

        self._update_status(f"clip_imported: {clip_name or file_path}")
        return True

    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip"""
        self.audio_mixer.remove_clip(clip_id)
        result = self.clip_manager.delete_clip(clip_id)

        if result:
            self._update_status(f"clip_deleted: {clip_id}")

        return result

    def play_clip(self, clip_id: str) -> bool:
        """Play a clip"""
        return self.audio_mixer.play_clip(clip_id)

    def stop_clip(self, clip_id: str) -> bool:
        """Stop a specific clip"""
        return self.audio_mixer.stop_clip(clip_id)

    def stop_all_clips(self) -> bool:
        """Stop all playing clips"""
        return self.audio_mixer.stop_all_clips()

    def assign_hotkey(self, clip_id: str, hotkey_string: str) -> bool:
        """
        Assign a hotkey to a clip

        Args:
            clip_id: ID of the clip
            hotkey_string: Hotkey string (e.g., "ctrl+alt+p")

        Returns:
            True if successful
        """
        # Validate hotkey input
        if not hotkey_string or not hotkey_string.strip():
            logger.error("Hotkey string cannot be empty")
            return False

        # Normalize hotkey to lowercase for consistency
        hotkey_normalized = hotkey_string.strip().lower()

        # Check if hotkey is already assigned to another clip
        hotkey_mapping = self.clip_manager.get_hotkey_mapping()
        for existing_hotkey, existing_clip_id in hotkey_mapping.items():
            if existing_hotkey.lower() == hotkey_normalized and existing_clip_id != clip_id:
                logger.error(f"Hotkey {hotkey_string} is already assigned to clip {existing_clip_id}")
                return False

        if not self.clip_manager.assign_hotkey(clip_id, hotkey_normalized):
            return False

        # Setup the hotkey in hotkey manager
        self.hotkey_manager.register_hotkey(
            hotkey_normalized, lambda cid=clip_id: self.audio_mixer.play_clip(cid)
        )

        logger.info(f"Assigned hotkey {hotkey_normalized} to clip {clip_id}")
        return True

    def unassign_hotkey(self, clip_id: str, hotkey_string: str) -> bool:
        """Unassign a hotkey from a clip"""
        if not self.clip_manager.unassign_hotkey(clip_id):
            return False

        self.hotkey_manager.unregister_hotkey(hotkey_string)
        logger.info(f"Unassigned hotkey {hotkey_string} from clip {clip_id}")
        return True

    def set_clip_volume(self, clip_id: str, volume: float) -> bool:
        """Set clip volume"""
        self.clip_manager.set_clip_volume(clip_id, volume)
        self.audio_mixer.set_clip_volume(clip_id, volume)
        return True

    def set_master_volume(self, volume: float):
        """Set master volume"""
        self.audio_mixer.set_master_volume(volume)

    def set_mic_volume(self, volume: float):
        """Set microphone volume"""
        self.audio_mixer.set_mic_volume(volume)

    def set_clip_volume_global(self, volume: float):
        """Set global volume for all clips"""
        self.audio_mixer.set_clip_volume_global(volume)

    def get_clips_list(self) -> Dict:
        """Get list of all clips with their metadata"""
        return self.clip_manager.get_all_clips_metadata()

    def get_status(self) -> Dict:
        """Get application status"""
        return {
            "app_running": self.is_running,
            "audio": self.audio_mixer.get_status(),
            "clips": len(self.clip_manager.clips_metadata),
        }

    def _load_clips_into_mixer(self):
        """Load all existing clips from clip manager into mixer"""
        all_metadata = self.clip_manager.get_all_clips_metadata()

        for clip_id, metadata in all_metadata.items():
            clip = self.clip_manager.load_audio_file(metadata.path)
            if clip:
                clip.volume = metadata.volume
                self.audio_mixer.add_clip(clip)

        logger.info(f"Loaded {len(all_metadata)} clips into mixer")

    def _setup_hotkeys(self):
        """Setup all registered hotkeys"""
        hotkey_mapping = self.clip_manager.get_hotkey_mapping()

        for hotkey, clip_id in hotkey_mapping.items():
            self.hotkey_manager.register_hotkey(
                hotkey, lambda cid=clip_id: self.audio_mixer.play_clip(cid)
            )

        # Register stop-all hotkey (default: Ctrl+Alt+S)
        self.hotkey_manager.register_hotkey(
            "ctrl+alt+s", self.audio_mixer.stop_all_clips
        )

        logger.info(f"Hotkeys setup complete ({len(hotkey_mapping)} clips)")

    def _audio_status_callback(self, status: str):
        """Handle audio status updates"""
        self._update_status(f"audio: {status}")

    def _on_hotkey_pressed(self, hotkey_string: str):
        """Handle hotkey press"""
        self._update_status(f"hotkey_pressed: {hotkey_string}")

    def _update_status(self, status: str):
        """Call status callback if provided"""
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")

    def cleanup(self):
        """Clean up resources"""
        if self.is_running:
            self.stop()

        self.audio_mixer.cleanup()
        self.hotkey_manager.cleanup()
        logger.info("App Controller cleaned up")
