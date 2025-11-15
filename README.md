# 🎵 Talkless - Audio Soundboard for Calls

A professional-grade Python audio application that lets you play sound effects, music clips, and audio samples during video calls. The audio is mixed with your microphone input and sent to your call application (Zoom, Google Meet, WhatsApp, Teams, etc.) making it sound like it's coming directly from your microphone.

## ✨ Features

- **🎼 Audio Clip Management** - Load and organize MP3, WAV, FLAC, OGG, and M4A files
- **⌨️ Global Hotkeys** - Assign keyboard shortcuts to clips, works even when app is minimized
- **🎛️ Real-Time Mixing** - Mix microphone audio + soundboard clips with zero echo or feedback
- **🔊 Volume Control** - Individual clip volumes + master volume + microphone volume control
- **⚡ Low Latency** - < 20ms latency for responsive playback during calls
- **🛑 Stop All** - Instantly stop all playing clips with a single hotkey
- **🎙️ VB-Cable Integration** - Works seamlessly with virtual audio cables

## 📋 Requirements

### System Requirements
- Python 3.8+
- macOS, Windows, or Linux
- VB-Cable or similar virtual audio driver

### Software Requirements
- PyAudio (for audio I/O)
- NumPy (for signal processing)
- SciPy (for audio algorithms)
- librosa (for audio file loading)
- pydub (for audio format support)
- PyQt6 (for UI)
- pynput (for global hotkeys)

## 🚀 Installation

### 1. Clone or Download the Repository

```bash
git clone https://github.com/yourusername/talkless.git
cd talkless
```

### 2. Install VB-Cable (Virtual Audio Driver)

**Windows:**
- Download from: https://vb-audio.com/Cable/
- Install and restart your computer
- Select "VB-Audio Virtual Cable" as your microphone in Zoom/Meet/Teams

**macOS:**
- Install BlackHole: https://github.com/ExistentialAudio/BlackHole
- Or SoundFlower: https://github.com/mattingall/Soundflower
- Configure as virtual microphone

**Linux:**
- Use PulseAudio or PipeWire virtual devices
- Enable loopback module if needed

### 3. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python talkless_gui.py
```

## 🎯 Usage

### Basic Workflow

1. **Launch Talkless** - Run the application
2. **Import Audio Files** - Click "Import Audio File" and select MP3/WAV/etc.
3. **Assign Hotkeys** (Optional) - Right-click a clip to assign a keyboard shortcut
4. **Configure Call App** - Select "VB-Audio Virtual Cable" as your microphone in Zoom/Meet
5. **Test** - Press hotkey or click "Play Selected" to hear audio on your call
6. **Use Stop All** - Press Ctrl+Alt+S (or your configured hotkey) to stop all sounds instantly

### Hotkey Examples

```
F1              - Play first clip
Ctrl+Alt+P      - Play background music
Shift+Space     - Play sound effect
Ctrl+Alt+S      - Stop all sounds (default)
```

### Volume Controls

- **Master Volume** - Controls overall output to call
- **Microphone Volume** - Control your voice level
- **Clips Volume** - Control all soundboard clips

## 🏗️ Project Structure

```
talkless/
├── talkless_gui.py              # Main PyQt6 GUI application
├── backend/
│   ├── audio_engine.py          # Core audio mixing (PyAudio + NumPy)
│   ├── clip_manager.py          # Audio file management
│   ├── hotkey_manager.py        # Global hotkey detection
│   ├── app_controller.py        # Main application orchestrator
│   └── __init__.py
├── data/
│   ├── clips/                   # Audio clip storage
│   └── metadata.json            # Clip metadata
├── assets/                      # Images and icons
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## ⚙️ Architecture

### Signal Flow

```
┌─────────────┐
│ Microphone  │
└──────┬──────┘
       │
       ├─────┐
       │     │
       │  ┌──┴─────────────────────┐
       │  │ Audio Mixer (NumPy)    │
       │  │ - Mix signals          │
       │  │ - Volume control       │
       │  │ - Prevent clipping     │
       │  └──┬────────────────────┬┘
       └────►│                    │
             │  Soundboard Clips  │
             │  (Loaded & Cached) │
             │                    │
             │ (VB-Cable Output)  │
             │    to Call App     │
```

### Components

**AudioMixer** (`audio_engine.py`)
- Real-time audio capture from microphone
- Multi-clip mixing with NumPy
- Low-latency output to VB-Cable
- Volume normalization

**ClipManager** (`clip_manager.py`)
- Load/save audio files (MP3, WAV, FLAC, OGG, M4A)
- Metadata persistence (JSON)
- Volume per-clip
- Hotkey assignments

**HotkeyManager** (`hotkey_manager.py`)
- Global hotkey detection via pynput
- Works when app is minimized
- Configurable hotkey combinations

**AppController** (`app_controller.py`)
- Orchestrates all subsystems
- API for UI interaction
- Status callbacks

## 🔊 Audio Configuration

### Latency Optimization

Current settings provide < 20ms latency:
- Sample Rate: 44.1kHz
- Buffer Size: 512 samples (~11ms)
- Processing time: < 9ms
- **Total: ~20ms** ✓

To adjust:
```python
# In audio_engine.py
SAMPLE_RATE = 44100      # Higher = better quality, more latency
CHUNK_SIZE = 512         # Lower = lower latency, more CPU
```

### Volume Levels

Volumes are normalized to 0.0 - 1.0 range:
- **0.0** = Mute
- **0.5** = 50% volume
- **1.0** = Full volume

Clipping prevention automatically applies to combined signal.

## 🐛 Troubleshooting

### No Audio Output
- [ ] Verify VB-Cable is installed
- [ ] Check that VB-Cable is selected as microphone in call app
- [ ] Check system volume levels
- [ ] Review logs in `logs/` directory

### Audio is Distorted
- [ ] Reduce Master Volume slider
- [ ] Reduce individual clip volumes
- [ ] Check microphone input level
- [ ] Lower overall system volume

### Hotkeys Not Working
- [ ] Grant microphone/input monitoring permissions
- [ ] Restart the application
- [ ] Try a different hotkey combination
- [ ] Check for hotkey conflicts with other apps

### High Latency
- [ ] Close other audio applications
- [ ] Reduce background processes
- [ ] Update audio drivers
- [ ] Reduce CHUNK_SIZE (may increase CPU)

### Crackling/Popping Audio
- [ ] Increase CHUNK_SIZE in config
- [ ] Reduce number of simultaneous clips
- [ ] Update audio drivers
- [ ] Lower Master Volume

## 🔒 Privacy & Security

- **No Cloud Upload** - All audio processing happens locally
- **No Analytics** - No user tracking or telemetry
- **Open Source** - Code is transparent and auditable
- **Local Storage** - Clips and metadata stored on your machine only

## 📝 API Reference

### AppController Main Methods

```python
from backend.app_controller import AppController

controller = AppController()

# Lifecycle
controller.start()          # Start audio engine and hotkeys
controller.stop()           # Stop everything

# Clip Management
controller.import_audio_file(path, name)  # Import audio file
controller.delete_clip(clip_id)           # Remove clip
controller.play_clip(clip_id)             # Play a clip
controller.stop_all_clips()               # Stop all playback

# Hotkeys
controller.assign_hotkey(clip_id, "ctrl+alt+p")
controller.unassign_hotkey(clip_id, "ctrl+alt+p")

# Volume Control
controller.set_master_volume(0.8)         # 0.0 to 1.0
controller.set_mic_volume(1.0)
controller.set_clip_volume_global(0.9)
controller.set_clip_volume(clip_id, 0.5) # Individual clip

# Status
status = controller.get_status()
clips = controller.get_clips_list()
```

## 🛠️ Development

### Adding New Features

1. **New Audio Effect?** - Add to `backend/audio_engine.py` in `_mix_clips()`
2. **New UI Tab?** - Add to `talkless_gui.py` in `create_*_tab()`
3. **New Hotkey Type?** - Extend `backend/hotkey_manager.py`

### Building Distribution

```bash
# Using PyInstaller for standalone executable
pip install pyinstaller
pyinstaller --onefile talkless_gui.py
```

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 🆘 Support

For issues and feature requests, please visit:
- GitHub Issues: https://github.com/yourusername/talkless/issues

## 🎓 Future Roadmap

- [ ] Automatic volume leveling (dynamic range compression)
- [ ] Audio effect plugins (reverb, EQ, effects)
- [ ] Clip categories/folders
- [ ] Favorites/quick access
- [ ] Recording capabilities
- [ ] Preset profiles
- [ ] Waveform visualization
- [ ] Cross-fade transitions
- [ ] Electron UI (Windows/macOS native)
- [ ] Mobile app

---

**Made with ❤️ for content creators, podcasters, and call enthusiasts**
