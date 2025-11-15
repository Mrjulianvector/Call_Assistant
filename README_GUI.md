# 🎵 Talkless Audio Soundboard - Complete Desktop Application

A pure Python desktop audio soundboard application with hotkey support, built with PyQt6.

## 🚀 Quick Start

### Installation & Setup
```bash
cd /Users/mahfoos/Projects/talkless

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run the application
python3 talkless_gui.py
```

## 📋 Features

### 🎹 **Soundboard Tab**
- **Import Audio Files** - Supports MP3, WAV, FLAC, OGG, M4A formats
- **Click to Play** - Click any clip in the list to play it instantly
- **Play Selected** - Button to play the selected clip
- **Stop Selected** - Stop the currently playing clip
- **Delete Clips** - Remove clips from the soundboard
- **Stop All** - Stop all playing sounds at once

### 🎛️ **Controls Tab**
- **Master Volume** (0-100%) - Overall output volume control
- **🎙️ Microphone Volume** (0-100%) - Mic input level control
- **Clips Volume** (0-100%) - Playback volume for all clips
- Real-time percentage display for all sliders

### ⌨️ **Hotkeys Tab**
- **Assign Hotkeys** - Bind keyboard shortcuts to clips (e.g., `ctrl+alt+1`)
- **Select Clip** - Dropdown to choose which clip to assign hotkey to
- **Hotkey Input** - Text field to enter hotkey combination
- **View Assignments** - List of all active hotkey bindings
- **Remove Hotkeys** - Delete hotkey assignments

### ⚙️ **Settings Tab**
- **Live Status Display** showing:
  - Number of clips loaded
  - Master volume percentage
  - Microphone volume percentage
  - Clips volume percentage

## 🎮 Usage Guide

### Importing a Clip
1. Go to **Soundboard** tab
2. Click **📁 Import Clip** button
3. Select an audio file (MP3, WAV, FLAC, OGG, M4A)
4. Enter a custom name or accept default
5. Click OK - clip appears in the list

### Playing Clips
- **Option 1:** Click directly on a clip in the list
- **Option 2:** Select a clip and click **▶️ Play Selected** button
- **Option 3:** Use hotkey if one is assigned (see below)

### Assigning a Hotkey
1. Go to **⌨️ Hotkeys** tab
2. Select a clip from the dropdown
3. Enter hotkey (e.g., `ctrl+alt+1`, `shift+f1`)
4. Click **🔑 Assign Hotkey**
5. Hotkey now works globally - press it anytime to play the clip

### Volume Control
1. Go to **🎛️ Controls** tab
2. Move sliders left/right to adjust:
   - Master volume (overall output)
   - Microphone volume (input level)
   - Clips volume (playback level)
3. Changes apply instantly

## 📁 Project Structure

```
talkless/
├── talkless_gui.py              # Main PyQt6 application
├── backend/
│   ├── app_controller.py        # Application orchestrator
│   ├── audio_engine.py          # Core audio processing
│   ├── clip_manager.py          # Clip file handling
│   ├── hotkey_manager.py        # Hotkey system
│   └── ui_main.py               # Legacy UI
├── data/
│   └── clips/                   # Imported clips stored here
├── venv/                        # Python virtual environment
└── requirements.txt             # Python dependencies
```

## 🔧 Architecture

### PyQt6 GUI (talkless_gui.py)
- **TalklessApp** - Main window class (QMainWindow)
- **AudioWorkerThread** - Background thread for status updates
- Multi-tab interface with real-time status

### Backend Modules
- **AppController** - Coordinates audio, clips, and hotkeys
- **AudioMixer** - Real-time audio mixing and playback
- **ClipManager** - File management and metadata
- **HotkeyManager** - Global hotkey handling

## 🎯 Supported Formats

| Format | Extension |
|--------|-----------|
| MP3 | `.mp3` |
| WAV | `.wav` |
| FLAC | `.flac` |
| OGG Vorbis | `.ogg` |
| M4A | `.m4a` |

## ⚙️ System Requirements

- Python 3.9+
- PyQt6
- PyAudio
- librosa (audio processing)
- numpy, scipy

## 🔌 Optional Hardware

- **VB-Cable** (Virtual Audio Device) - For routing audio to apps
- **Microphone** - For input capture (optional)

## 📊 Status Display

The Settings tab shows real-time metrics:
- Clips loaded in memory
- Current master volume
- Current microphone volume
- Current clips playback volume

## 🚦 Hotkey Format Examples

```
ctrl+alt+1         # Control + Alt + 1
shift+f1           # Shift + F1
ctrl+shift+p       # Control + Shift + P
alt+x              # Alt + X
```

## 🔒 Data Storage

- Clips are stored in `data/clips/` directory
- Metadata (names, hotkeys, volumes) saved in JSON format
- All data persists between sessions

## 💡 Tips & Tricks

1. **Quick Play** - Click directly on clip name instead of using button
2. **Volume Control** - Sliders are smooth and responsive
3. **Multiple Hotkeys** - Can have one hotkey per clip
4. **Organize Clips** - Name your imported clips clearly
5. **Delete Old Clips** - Remove unused clips to free up memory

## 🐛 Troubleshooting

### "No input device available"
- This is normal if you don't have a microphone connected
- Mic volume control still works but won't capture audio

### "VB-Cable not found"
- Optional - only needed if you want to route audio to other applications
- Application works fine without it

### Hotkey not working
- Make sure application window is active or in focus
- Check hotkey format (use + between keys)
- Try a different hotkey combination

## 📝 Notes

- Audio processing runs in separate threads for smooth UI
- Status updates every 500ms
- Clips can be played simultaneously
- All operations are logged for debugging

## 🎊 Complete & Ready to Use!

The Talkless audio soundboard is fully functional with all features working:
- ✅ Import/delete clips
- ✅ Play/stop controls
- ✅ Volume management
- ✅ Hotkey system
- ✅ Real-time status display
- ✅ Multi-clip playback

Enjoy your audio soundboard!
