"""
Audio Mixing Engine - Core audio processing for Talkless
Handles microphone capture, clip playback, and real-time mixing to VB-Cable
"""

import pyaudio
import numpy as np
import threading
import queue
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio configuration constants
SAMPLE_RATE = 44100
CHUNK_SIZE = 512  # ~11ms at 44.1kHz (well under 20ms requirement)
CHANNELS = 1
AUDIO_FORMAT = pyaudio.paFloat32
MAX_CLIPS = 10
VOLUME_RANGE = (0.0, 1.0)


class AudioState(Enum):
    """Audio engine states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class AudioClip:
    """Represents an audio clip in memory"""
    id: str
    name: str
    audio_data: np.ndarray  # Audio samples as numpy array
    duration: float  # In seconds
    volume: float = 1.0  # 0.0 to 1.0
    is_playing: bool = False
    playback_position: int = 0  # Current sample index


class VBCableManager:
    """Manages VB-Cable device detection and routing"""

    @staticmethod
    def find_vb_cable_input_device() -> Optional[int]:
        """Find VB-Cable Input device index"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            device_name = info.get("name", "").lower()

            # Check for various VB-Cable naming conventions
            if "vb" in device_name and "cable" in device_name:
                if info.get("maxInputChannels", 0) > 0:
                    logger.info(f"Found VB-Cable Input at device {i}: {info['name']}")
                    p.terminate()
                    return i

        p.terminate()
        logger.warning("VB-Cable Input device not found. Install VB-Audio Cable.")
        return None

    @staticmethod
    def find_microphone_device() -> Optional[int]:
        """Find default microphone input device"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        for i in range(device_count):
            info = p.get_device_info_by_index(i)

            # Prefer device with "Microphone" in name or default input
            if (
                info.get("maxInputChannels", 0) > 0
                and "microphone" in info.get("name", "").lower()
            ):
                logger.info(f"Found Microphone at device {i}: {info['name']}")
                p.terminate()
                return i

        # Fall back to default input device
        try:
            default_input = p.get_default_input_device_info()
            p.terminate()
            logger.info(f"Using default input device: {default_input['name']}")
            return default_input["index"]
        except OSError:
            p.terminate()
            logger.warning("No input device available - microphone input disabled")
            return None  # Return None to indicate no device available


class AudioMixer:
    """Core audio mixing engine"""

    def __init__(self, status_callback: Optional[Callable] = None):
        """
        Initialize audio mixer

        Args:
            status_callback: Optional callback for status updates
        """
        self.pyaudio_instance = pyaudio.PyAudio()
        self.status_callback = status_callback
        self.state = AudioState.STOPPED

        # Find devices
        self.mic_device = VBCableManager.find_microphone_device()
        self.vb_cable_device = VBCableManager.find_vb_cable_input_device()

        # If VB-Cable not found, use default output device
        if not self.vb_cable_device:
            logger.warning("VB-Cable not found - using default system audio output")
            try:
                self.vb_cable_device = self.pyaudio_instance.get_default_output_device_info()["index"]
                logger.info(f"Using default output device: {self.pyaudio_instance.get_device_info_by_index(self.vb_cable_device)['name']}")
            except:
                logger.warning("Could not find default output device")

        # Audio streams
        self.input_stream = None
        self.output_stream = None

        # Clip management
        self.clips: dict[str, AudioClip] = {}
        self.active_clips: list[str] = []
        self.clip_queue = queue.Queue()

        # Threading
        self.audio_thread = None
        self.stop_event = threading.Event()
        self.is_running = False

        # Volume control
        self.master_volume = 1.0
        self.mic_volume = 1.0
        self.clip_volume = 1.0

        logger.info("Audio Mixer initialized")

    def start(self) -> bool:
        """Start audio processing"""
        if self.is_running:
            logger.warning("Audio mixer already running")
            return False

        try:
            # Open input stream (microphone) - only if device available
            if self.mic_device is not None:
                try:
                    self.input_stream = self.pyaudio_instance.open(
                        format=AUDIO_FORMAT,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        input=True,
                        input_device_index=self.mic_device,
                        frames_per_buffer=CHUNK_SIZE,
                        stream_callback=None,
                    )
                    logger.info(f"Input stream opened on device {self.mic_device}")
                except Exception as e:
                    logger.warning(f"Failed to open microphone input: {e} - running without microphone")
                    self.input_stream = None
            else:
                logger.warning("No microphone device available - running without microphone input")
                self.input_stream = None

            # Open output stream
            if self.vb_cable_device is not None:
                self.output_stream = self.pyaudio_instance.open(
                    format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    output=True,
                    output_device_index=self.vb_cable_device,
                    frames_per_buffer=CHUNK_SIZE,
                )
                logger.info(f"Output stream opened on device {self.vb_cable_device}")
            else:
                logger.error("No output device available - cannot start audio")
                return False

            self.is_running = True
            self.stop_event.clear()
            self.state = AudioState.RUNNING

            # Start audio processing thread
            self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
            self.audio_thread.start()

            logger.info("Audio mixer started")
            self._update_status("started")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio mixer: {e}")
            self._update_status(f"error: {e}")
            return False

    def stop(self) -> bool:
        """Stop audio processing"""
        if not self.is_running:
            logger.warning("Audio mixer not running")
            return False

        self.stop_event.set()
        self.is_running = False
        self.state = AudioState.STOPPED

        # Wait for thread to finish
        if self.audio_thread:
            self.audio_thread.join(timeout=2.0)

        # Close streams
        try:
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
        except Exception as e:
            logger.error(f"Error closing streams: {e}")

        logger.info("Audio mixer stopped")
        self._update_status("stopped")
        return True

    def add_clip(self, clip: AudioClip) -> bool:
        """Add an audio clip to the mixer"""
        if len(self.clips) >= MAX_CLIPS:
            logger.warning(f"Maximum clips ({MAX_CLIPS}) reached")
            return False

        self.clips[clip.id] = clip
        logger.info(f"Clip added: {clip.name} (ID: {clip.id})")
        return True

    def remove_clip(self, clip_id: str) -> bool:
        """Remove an audio clip"""
        if clip_id in self.clips:
            del self.clips[clip_id]
            # Stop playback if playing
            if clip_id in self.active_clips:
                self.active_clips.remove(clip_id)
            logger.info(f"Clip removed: {clip_id}")
            return True
        return False

    def play_clip(self, clip_id: str) -> bool:
        """Queue a clip for playback"""
        if clip_id not in self.clips:
            logger.warning(f"Clip not found: {clip_id}")
            return False

        clip = self.clips[clip_id]

        # Reset playback position
        clip.playback_position = 0
        clip.is_playing = True

        if clip_id not in self.active_clips:
            self.active_clips.append(clip_id)

        logger.info(f"Playing clip: {clip.name}")
        self._update_status(f"playing: {clip.name}")
        return True

    def stop_clip(self, clip_id: str) -> bool:
        """Stop playback of a specific clip"""
        if clip_id in self.active_clips:
            self.active_clips.remove(clip_id)
            if clip_id in self.clips:
                self.clips[clip_id].is_playing = False
                self.clips[clip_id].playback_position = 0
            logger.info(f"Stopped clip: {clip_id}")
            return True
        return False

    def stop_all_clips(self) -> bool:
        """Stop all currently playing clips"""
        stopped_count = len(self.active_clips)
        for clip_id in self.active_clips:
            if clip_id in self.clips:
                self.clips[clip_id].is_playing = False
                self.clips[clip_id].playback_position = 0

        self.active_clips.clear()
        logger.info(f"Stopped {stopped_count} clips")
        self._update_status("all_clips_stopped")
        return True

    def set_clip_volume(self, clip_id: str, volume: float) -> bool:
        """Set volume for a specific clip (0.0 to 1.0)"""
        if clip_id not in self.clips:
            return False

        volume = max(0.0, min(1.0, volume))
        self.clips[clip_id].volume = volume
        logger.info(f"Set clip volume: {clip_id} -> {volume:.2f}")
        return True

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)"""
        self.master_volume = max(0.0, min(1.0, volume))
        logger.info(f"Master volume: {self.master_volume:.2f}")

    def set_mic_volume(self, volume: float):
        """Set microphone input volume (0.0 to 1.0)"""
        self.mic_volume = max(0.0, min(1.0, volume))
        logger.info(f"Mic volume: {self.mic_volume:.2f}")

    def set_clip_volume_global(self, volume: float):
        """Set global volume for all clips (0.0 to 1.0)"""
        self.clip_volume = max(0.0, min(1.0, volume))
        logger.info(f"Clip global volume: {self.clip_volume:.2f}")

    def _audio_loop(self):
        """Main audio processing loop (runs in separate thread)"""
        logger.info("Audio loop started")
        mic_error_count = 0
        max_mic_errors = 10

        try:
            while not self.stop_event.is_set():
                # Read from microphone (if available)
                if self.input_stream:
                    try:
                        mic_data = self.input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        mic_signal = np.frombuffer(mic_data, dtype=np.float32)
                        mic_error_count = 0  # Reset error count on success
                    except Exception as e:
                        mic_error_count += 1
                        if mic_error_count <= max_mic_errors:
                            logger.debug(f"Microphone read error ({mic_error_count}/{max_mic_errors}): {e}")
                        elif mic_error_count == max_mic_errors + 1:
                            logger.warning(f"Mic errors exceeded threshold, suppressing further warnings")
                        mic_signal = np.zeros(CHUNK_SIZE, dtype=np.float32)
                else:
                    # No microphone input available
                    mic_signal = np.zeros(CHUNK_SIZE, dtype=np.float32)

                # Mix active clips
                mixed_clips = self._mix_clips(CHUNK_SIZE)

                # Combine signals: microphone + clips
                combined_signal = (mic_signal * self.mic_volume) + (mixed_clips * self.clip_volume)

                # Apply master volume and prevent clipping
                combined_signal = combined_signal * self.master_volume
                combined_signal = np.clip(combined_signal, -1.0, 1.0)

                # Send to output
                if self.output_stream:
                    try:
                        output_data = combined_signal.astype(np.float32)
                        self.output_stream.write(output_data.tobytes())
                    except Exception as e:
                        logger.error(f"Error writing to output: {e}")

        except Exception as e:
            logger.error(f"Audio loop error: {e}")
            self._update_status(f"error: {e}")
        finally:
            logger.info("Audio loop ended")

    def _mix_clips(self, chunk_size: int) -> np.ndarray:
        """Mix all active clips into a single audio signal"""
        mixed = np.zeros(chunk_size, dtype=np.float32)

        for clip_id in self.active_clips[:]:  # Copy list to avoid modification during iteration
            if clip_id not in self.clips:
                self.active_clips.remove(clip_id)
                continue

            clip = self.clips[clip_id]
            clip_audio = clip.audio_data

            # Calculate how many samples we can read
            remaining_samples = len(clip_audio) - clip.playback_position
            samples_to_read = min(chunk_size, remaining_samples)

            if samples_to_read <= 0:
                # Clip finished playing
                clip.is_playing = False
                self.active_clips.remove(clip_id)
                continue

            # Get samples from clip
            clip_chunk = clip_audio[
                clip.playback_position : clip.playback_position + samples_to_read
            ]

            # Apply clip-specific volume
            clip_chunk = clip_chunk * clip.volume

            # Add to mix (pad with zeros if clip is shorter than chunk)
            mixed[:samples_to_read] += clip_chunk
            clip.playback_position += samples_to_read

        return mixed

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

        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            logger.info("PyAudio terminated")

    def get_status(self) -> dict:
        """Get current mixer status"""
        return {
            "state": self.state.value,
            "is_running": self.is_running,
            "active_clips": len(self.active_clips),
            "total_clips": len(self.clips),
            "master_volume": self.master_volume,
            "mic_volume": self.mic_volume,
            "clip_volume": self.clip_volume,
        }
