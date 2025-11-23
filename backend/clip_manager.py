"""
Clip Manager - Audio file loading, metadata extraction, and clip management
"""

import os
import librosa
import numpy as np
from typing import Optional, Dict
from pathlib import Path
from dataclasses import dataclass
import logging
import json
from .audio_engine import AudioClip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
DEFAULT_SAMPLE_RATE = 48000  # Matches system audio device sample rates


@dataclass
class ClipMetadata:
    """Metadata for an audio clip"""

    name: str
    path: str
    duration: float
    sample_rate: int
    channels: int
    hotkey: Optional[str] = None
    volume: float = 1.0


class ClipManager:
    """Manages loading, saving, and organizing audio clips"""

    def __init__(self, clips_dir: str = "data/clips"):
        """
        Initialize clip manager

        Args:
            clips_dir: Directory where audio clips are stored
        """
        self.clips_dir = Path(clips_dir)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.clips_dir / "metadata.json"
        self.clips_metadata: Dict[str, ClipMetadata] = {}

        self._load_metadata()
        logger.info(f"Clip Manager initialized with directory: {self.clips_dir}")

    def load_audio_file(self, file_path: str) -> Optional[AudioClip]:
        """
        Load an audio file and create an AudioClip object

        Args:
            file_path: Path to audio file

        Returns:
            AudioClip object or None if load fails
        """
        path = Path(file_path)

        # Validate file
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        if path.suffix.lower() not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {path.suffix}")
            return None

        try:
            # Load audio file
            audio_data, sr = librosa.load(file_path, sr=DEFAULT_SAMPLE_RATE, mono=True)

            # Convert to float32
            audio_data = audio_data.astype(np.float32)

            # Calculate duration
            duration = len(audio_data) / DEFAULT_SAMPLE_RATE

            # Create clip
            clip_id = path.stem
            clip = AudioClip(
                id=clip_id,
                name=path.stem,
                audio_data=audio_data,
                duration=duration,
                volume=1.0,
            )

            logger.info(
                f"Loaded clip: {clip.name} ({duration:.2f}s @ {DEFAULT_SAMPLE_RATE}Hz)"
            )
            return clip

        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            return None

    def import_clip(self, source_path: str, clip_name: Optional[str] = None) -> bool:
        """
        Import an audio file into the clips directory

        Args:
            source_path: Path to source audio file
            clip_name: Optional custom name for the clip

        Returns:
            True if import successful
        """
        source = Path(source_path)

        if not source.exists():
            logger.error(f"Source file not found: {source_path}")
            return False

        if source.suffix.lower() not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {source.suffix}")
            return False

        try:
            # Determine destination name
            dest_name = clip_name or source.stem
            dest_path = self.clips_dir / f"{dest_name}{source.suffix}"

            # Copy file
            import shutil

            shutil.copy2(source, dest_path)

            # Load and create clip
            clip = self.load_audio_file(str(dest_path))
            if not clip:
                return False

            # Save metadata
            metadata = ClipMetadata(
                name=dest_name,
                path=str(dest_path),
                duration=clip.duration,
                sample_rate=DEFAULT_SAMPLE_RATE,
                channels=1,
            )
            self.clips_metadata[clip.id] = metadata
            self._save_metadata()

            logger.info(f"Imported clip: {dest_name}")
            return True

        except Exception as e:
            logger.error(f"Error importing clip: {e}")
            return False

    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip"""
        if clip_id not in self.clips_metadata:
            logger.warning(f"Clip not found: {clip_id}")
            return False

        try:
            metadata = self.clips_metadata[clip_id]
            clip_path = Path(metadata.path)

            # Delete file
            if clip_path.exists():
                clip_path.unlink()

            # Remove metadata
            del self.clips_metadata[clip_id]
            self._save_metadata()

            logger.info(f"Deleted clip: {clip_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting clip: {e}")
            return False

    def assign_hotkey(self, clip_id: str, hotkey: str) -> bool:
        """Assign a hotkey to a clip"""
        if clip_id not in self.clips_metadata:
            logger.warning(f"Clip not found: {clip_id}")
            return False

        # Check if hotkey already assigned
        for cid, metadata in self.clips_metadata.items():
            if cid != clip_id and metadata.hotkey == hotkey:
                logger.warning(f"Hotkey already assigned to {cid}")
                return False

        self.clips_metadata[clip_id].hotkey = hotkey
        self._save_metadata()
        logger.info(f"Assigned hotkey '{hotkey}' to clip '{clip_id}'")
        return True

    def unassign_hotkey(self, clip_id: str) -> bool:
        """Remove hotkey assignment from a clip"""
        if clip_id not in self.clips_metadata:
            return False

        self.clips_metadata[clip_id].hotkey = None
        self._save_metadata()
        logger.info(f"Removed hotkey from clip '{clip_id}'")
        return True

    def set_clip_volume(self, clip_id: str, volume: float) -> bool:
        """Set clip volume"""
        if clip_id not in self.clips_metadata:
            return False

        volume = max(0.0, min(1.0, volume))
        self.clips_metadata[clip_id].volume = volume
        self._save_metadata()
        return True

    def get_clip_metadata(self, clip_id: str) -> Optional[ClipMetadata]:
        """Get metadata for a clip"""
        return self.clips_metadata.get(clip_id)

    def get_all_clips_metadata(self) -> Dict[str, ClipMetadata]:
        """Get metadata for all clips"""
        return self.clips_metadata.copy()

    def get_hotkey_mapping(self) -> Dict[str, str]:
        """Get mapping of hotkeys to clip IDs"""
        mapping = {}
        for clip_id, metadata in self.clips_metadata.items():
            if metadata.hotkey:
                mapping[metadata.hotkey] = clip_id
        return mapping

    def _load_metadata(self):
        """Load metadata from file"""
        if not self.metadata_file.exists():
            logger.info("No existing metadata file")
            return

        try:
            with open(self.metadata_file, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error("Invalid metadata format: expected dictionary")
                return

            loaded_count = 0
            for clip_id, meta_dict in data.items():
                try:
                    # Validate required fields
                    if not isinstance(meta_dict, dict):
                        logger.warning(f"Skipping invalid metadata entry for {clip_id}: not a dictionary")
                        continue

                    # Check required fields
                    required_fields = ["name", "path", "duration", "sample_rate", "channels"]
                    for field in required_fields:
                        if field not in meta_dict:
                            logger.warning(f"Skipping metadata for {clip_id}: missing required field '{field}'")
                            continue

                    metadata = ClipMetadata(**meta_dict)
                    self.clips_metadata[clip_id] = metadata
                    loaded_count += 1
                except Exception as e:
                    logger.warning(f"Skipping invalid metadata entry for {clip_id}: {e}")
                    continue

            logger.info(f"Loaded metadata for {loaded_count} clips")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing metadata JSON: {e}")
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")

    def _save_metadata(self):
        """Save metadata to file"""
        try:
            data = {}
            for clip_id, metadata in self.clips_metadata.items():
                data[clip_id] = {
                    "name": metadata.name,
                    "path": metadata.path,
                    "duration": metadata.duration,
                    "sample_rate": metadata.sample_rate,
                    "channels": metadata.channels,
                    "hotkey": metadata.hotkey,
                    "volume": metadata.volume,
                }

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Metadata saved")

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
