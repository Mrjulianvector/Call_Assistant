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
SAMPLE_RATE = 48000  # 48kHz matches most system audio devices
CHUNK_SIZE = 512  # ~10.7ms at 48kHz (well under 20ms requirement)
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
    def find_output_device() -> Optional[int]:
        """Find output device (prefer VB-Cable for virtual audio routing to calls)"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        vb_cable_device = None

        logger.info(f"🔍 Scanning {device_count} devices for VB-Cable output...")

        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            device_name = info.get("name", "").lower()

            # Look for VB-Cable first (for virtual audio routing to calls)
            if info.get("maxOutputChannels", 0) > 0:
                logger.debug(f"  Device {i}: {info['name']} (output channels: {info.get('maxOutputChannels', 0)})")
                if "vb" in device_name and "cable" in device_name:
                    vb_cable_device = i
                    logger.info(f"✓ Found VB-Cable at device {i}: {info['name']}")
                    break

        p.terminate()

        if vb_cable_device is not None:
            logger.info("✓ Using VB-Cable for virtual audio routing to calls")
            return vb_cable_device
        else:
            logger.warning("✗ No VB-Cable found - clips will not be routed to calls")
            return None

    @staticmethod
    def find_monitoring_device() -> Optional[int]:
        """Find monitoring device (headphones/AirPods for user monitoring)"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        headphones_device = None
        realtek_device = None
        airpods_device = None
        speakers_device = None
        other_output = None

        # On Windows, Bluetooth AirPods are unreliable - prioritize wired/Realtek devices
        is_windows = sys.platform == "win32"
        platform_name = "Windows" if is_windows else "macOS"

        logger.info(f"🔍 Scanning {device_count} devices for monitoring output on {platform_name}...")

        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                # Safely decode device name, handling encoding issues on Windows
                try:
                    device_name = info.get("name", "").lower()
                except (UnicodeDecodeError, UnicodeEncodeError):
                    device_name = str(info.get("name", "")).lower()

                # Check for output capability
                if info.get("maxOutputChannels", 0) > 0:
                    logger.debug(f"  Device {i}: {info['name']} (output)")

                    # On Windows, prioritize Realtek (wired headphones)
                    if is_windows and "realtek" in device_name and "headphone" in device_name:
                        if realtek_device is None:
                            realtek_device = i
                            logger.info(f"  ✓ Found Realtek headphones at device {i}: {info['name']}")
                        continue

                    # On macOS, prefer AirPods/EarPods
                    if not is_windows and ("earpods" in device_name or "airpods" in device_name):
                        airpods_device = i
                        logger.info(f"  ✓ Found EarPods/AirPods at device {i}: {info['name']}")
                        continue

                    # For Windows, still collect AirPods but deprioritize
                    if "earpods" in device_name or "airpods" in device_name:
                        if airpods_device is None:
                            airpods_device = i
                            logger.info(f"  ⚠ Found AirPods/EarPods at device {i}: {info['name']} (may be unreliable on Windows)")
                        continue

                    # Then regular headphones
                    if "headphone" in device_name:
                        if headphones_device is None:
                            headphones_device = i
                            logger.info(f"  ✓ Found headphones at device {i}: {info['name']}")
                        continue

                    # Look for speakers
                    if "speaker" in device_name or "built-in" in device_name:
                        if speakers_device is None:
                            speakers_device = i
                            logger.info(f"  🔊 Found speakers at device {i}: {info['name']}")
                        continue

                    # Keep track of other devices (not VB-Cable, not HDMI)
                    if ("vb" not in device_name and "hdmi" not in device_name and other_output is None):
                        other_output = i
                        logger.debug(f"  Other device at {i}: {info['name']}")
            except Exception as e:
                logger.debug(f"Error processing device {i}: {e}")
                continue

        p.terminate()

        # Priority order depends on OS
        if is_windows:
            # Windows: Realtek > regular headphones > speakers > other > AirPods (unreliable on Windows)
            logger.info("📋 Windows priority: Realtek > Headphones > Speakers > Other > AirPods")
            if realtek_device is not None:
                logger.info(f"✓ Selected: Realtek headphones (device {realtek_device})")
                return realtek_device
            elif headphones_device is not None:
                logger.info(f"✓ Selected: Headphones (device {headphones_device})")
                return headphones_device
            elif speakers_device is not None:
                logger.info(f"✓ Selected: Built-in speakers (device {speakers_device})")
                return speakers_device
            elif other_output is not None:
                logger.info(f"✓ Selected: Other output device (device {other_output})")
                return other_output
            elif airpods_device is not None:
                logger.warning(f"⚠ Selected: AirPods/Bluetooth (device {airpods_device}) - may be unreliable")
                return airpods_device
            else:
                logger.error("✗ No monitoring device found - user will not hear clips")
                return None
        else:
            # macOS: AirPods > headphones > speakers > other
            logger.info("📋 macOS priority: AirPods > Headphones > Speakers > Other")
            if airpods_device is not None:
                logger.info(f"✓ Selected: AirPods/EarPods (device {airpods_device})")
                return airpods_device
            elif headphones_device is not None:
                logger.info(f"✓ Selected: Headphones (device {headphones_device})")
                return headphones_device
            elif speakers_device is not None:
                logger.info(f"✓ Selected: Built-in speakers (device {speakers_device})")
                return speakers_device
            elif other_output is not None:
                logger.info(f"✓ Selected: Other output device (device {other_output})")
                return other_output
            else:
                logger.error("✗ No monitoring device found - user will not hear clips")
                return None

    @staticmethod
    def find_microphone_device() -> Optional[int]:
        """Find default microphone input device"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        logger.info(f"🔍 Scanning {device_count} devices for microphone input...")

        # First, look for dedicated microphone device
        for i in range(device_count):
            info = p.get_device_info_by_index(i)

            if (
                info.get("maxInputChannels", 0) > 0
                and "microphone" in info.get("name", "").lower()
            ):
                logger.info(f"✓ Found dedicated Microphone at device {i}: {info['name']}")
                p.terminate()
                return i

        # Second, look for any input device that's NOT VB-Cable
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            device_name = info.get("name", "").lower()

            if (
                info.get("maxInputChannels", 0) > 0
                and "vb-cable" not in device_name
                and "vb" not in device_name
            ):
                logger.info(f"✓ Using input device: {info['name']} (device {i})")
                p.terminate()
                return i

        # Fall back to default input device (even if it's VB-Cable - with warning)
        try:
            default_input = p.get_default_input_device_info()
            device_name = default_input.get("name", "").lower()

            if "vb-cable" in device_name or "vb" in device_name:
                logger.warning(
                    f"⚠️ Using VB-Cable as input device: {default_input['name']}. "
                    "This is likely wrong - you probably need a USB microphone or built-in mic. "
                    "Check your audio device settings."
                )
            else:
                logger.info(f"✓ Using default input device: {default_input['name']} (device {default_input['index']})")

            p.terminate()
            return default_input["index"]
        except OSError:
            p.terminate()
            logger.error(
                "❌ No input device available - microphone input disabled. "
                "Please connect a microphone or USB audio device."
            )
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

        logger.info("="*60)
        logger.info("🎵 AUDIO MIXER INITIALIZATION")
        logger.info("="*60)

        # Find devices
        self.mic_device = VBCableManager.find_microphone_device()
        self.output_device = VBCableManager.find_output_device()

        # Find monitoring device (for user to hear clips - EarPods/headphones)
        self.monitoring_device = VBCableManager.find_monitoring_device()

        # Keep system speakers for fallback only
        self.system_speakers_device = self._find_system_speakers()

        # Fallback to default output if not found
        if not self.output_device:
            try:
                self.output_device = self.pyaudio_instance.get_default_output_device_info()["index"]
                logger.info(f"✓ Using default output device: {self.pyaudio_instance.get_device_info_by_index(self.output_device)['name']}")
            except:
                logger.warning("✗ Could not find any output device")

        # Audio streams
        self.input_stream = None
        self.output_stream = None
        self.speakers_stream = None  # Secondary output for system speakers

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

        # Log device summary
        logger.info("="*60)
        logger.info("📋 DEVICE CONFIGURATION SUMMARY:")
        logger.info(f"  Microphone Input:     Device {self.mic_device}" if self.mic_device is not None else "  Microphone Input:     DISABLED")
        logger.info(f"  Call Output (VB-Cable): Device {self.output_device}" if self.output_device is not None else "  Call Output:          NOT FOUND")
        logger.info(f"  Local Monitoring:     Device {self.monitoring_device}" if self.monitoring_device is not None else "  Local Monitoring:     NOT FOUND")
        logger.info("="*60)
        logger.info("✓ Audio Mixer initialized")

    def _find_system_speakers(self) -> Optional[int]:
        """Find system speakers device"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()

        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            device_name = info.get("name", "").lower()

            if info.get("maxOutputChannels", 0) > 0:
                if any(x in device_name for x in ["speaker", "headphone", "airpods"]):
                    p.terminate()
                    logger.info(f"Found system speakers at device {i}: {info['name']}")
                    return i

        p.terminate()
        return None

    def _open_monitoring_stream_with_fallback(self):
        """
        Try to open monitoring stream with multiple fallbacks.
        On Windows, tries multiple devices if the first one fails.
        Falls back to built-in speakers if headphones not available.
        """
        devices_to_try = []

        # Add primary monitoring device first
        if self.monitoring_device is not None:
            devices_to_try.append(self.monitoring_device)
            logger.info(f"📢 Primary monitoring device: {self.monitoring_device}")

        # On Windows, add comprehensive fallback devices
        if sys.platform == "win32":
            logger.info("🔧 Building fallback device list for Windows...")
            # Try default output device
            try:
                default_output_info = self.pyaudio_instance.get_default_output_device_info()
                default_device = default_output_info["index"]
                if default_device != self.output_device and default_device not in devices_to_try:
                    devices_to_try.append(default_device)
                    logger.info(f"  Added fallback: Default device {default_device}")
            except Exception as e:
                logger.debug(f"  Could not get default output: {e}")

            # Collect all possible output devices organized by type
            realtek_devices = []
            headphone_devices = []
            speaker_devices = []
            other_devices = []

            try:
                p = pyaudio.PyAudio()
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if info.get("maxOutputChannels", 0) > 0 and i != self.output_device and i not in devices_to_try:
                        try:
                            device_name = info.get("name", "").lower()
                        except:
                            device_name = str(info.get("name", "")).lower()

                        # Categorize devices
                        if "realtek" in device_name:
                            if "headphone" in device_name:
                                realtek_devices.append(i)
                                logger.info(f"  Added fallback: Realtek headphones (device {i})")
                            else:
                                realtek_devices.append(i)
                                logger.info(f"  Added fallback: Realtek device (device {i})")
                        elif "headphone" in device_name:
                            headphone_devices.append(i)
                            logger.info(f"  Added fallback: Headphones (device {i})")
                        elif "speaker" in device_name or "built-in" in device_name:
                            speaker_devices.append(i)
                            logger.info(f"  Added fallback: Speakers (device {i})")
                        else:
                            other_devices.append(i)
                            logger.debug(f"  Added fallback: Other device {i}")
                p.terminate()
            except Exception as e:
                logger.debug(f"Error collecting fallback devices: {e}")

            # Add in priority order: Realtek > Headphones > Speakers > Others
            devices_to_try.extend(realtek_devices)
            devices_to_try.extend(headphone_devices)
            devices_to_try.extend(speaker_devices)
            devices_to_try.extend(other_devices)

        logger.info(f"🔄 Attempting to open monitoring stream on {len(devices_to_try)} device(s)...")
        # Try each device in order
        for idx, device_id in enumerate(devices_to_try, 1):
            try:
                device_info = self.pyaudio_instance.get_device_info_by_index(device_id)
                logger.info(f"  [{idx}/{len(devices_to_try)}] Trying device {device_id}: {device_info['name']}")
                stream = self.pyaudio_instance.open(
                    format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    output=True,
                    output_device_index=device_id,
                    frames_per_buffer=CHUNK_SIZE,
                )
                logger.info(f"✅ SUCCESS! Monitoring stream opened on device {device_id}: {device_info['name']}")
                return stream
            except Exception as e:
                logger.warning(f"  ✗ Failed on device {device_id}: {type(e).__name__}: {e}")
                continue

        # If all devices failed
        logger.error("❌ Could not open monitoring stream on ANY device - audio will be sent ONLY to VB-Cable")
        return None

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

            # Open primary output stream (VB-Cable for virtual calls)
            if self.output_device is not None:
                self.output_stream = self.pyaudio_instance.open(
                    format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    output=True,
                    output_device_index=self.output_device,
                    frames_per_buffer=CHUNK_SIZE,
                )
                logger.info(f"Output stream opened on device {self.output_device}")
            else:
                logger.error("No output device available - cannot start audio")
                return False

            # Open monitoring output stream (user's headphones/EarPods for local monitoring)
            # This allows the user to hear their clips in real-time
            if self.monitoring_device is not None and self.monitoring_device != self.output_device:
                self.speakers_stream = self._open_monitoring_stream_with_fallback()
            else:
                if self.monitoring_device is None:
                    logger.info("No monitoring device found - audio will be sent only to VB-Cable")
                    self.speakers_stream = None
                else:
                    logger.info("Monitoring device same as output device - single stream will be used")
                    self.speakers_stream = None

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
            if self.speakers_stream:
                self.speakers_stream.stop_stream()
                self.speakers_stream.close()
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

                # Send to output (both primary and speakers)
                output_data = combined_signal.astype(np.float32)
                output_bytes = output_data.tobytes()

                if self.output_stream:
                    try:
                        self.output_stream.write(output_bytes)
                    except Exception as e:
                        logger.error(f"Error writing to primary output: {e}")

                if self.speakers_stream:
                    try:
                        self.speakers_stream.write(output_bytes)
                    except Exception as e:
                        logger.error(f"Error writing to speakers: {e}")

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
