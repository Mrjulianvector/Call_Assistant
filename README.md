# Call Assistant - Audio Soundboard

A powerful desktop audio soundboard designed for seamless integration with video/audio conferencing platforms (Zoom, Google Meet, WhatsApp, Teams, etc.). Mix microphone audio with pre-recorded soundboard clips and route the combined signal to your call platform.

## Features

### Core Functionality
- **Audio File Management**: Load and manage MP3, WAV, FLAC, OGG, M4A audio files
- **Real-time Audio Mixing**: Combine microphone input with soundboard clips simultaneously
- **Global Hotkeys**: Assign keyboard shortcuts to instantly trigger audio clips during calls
- **VB-Cable Integration**: Route mixed audio to virtual microphone for call platforms
- **Volume Control**:
  - Master volume control
  - Microphone volume adjustment
  - Individual clip volume control
  - Global clip volume control

### Audio Quality
- **Low Latency**: ~11ms processing latency (well under 20ms requirement)
- **No Echo/Feedback**: Separate audio paths ensure clean signal
- **Clipping Prevention**: Automatic audio normalization to prevent distortion
- **Multi-clip Playback**: Play multiple clips simultaneously with proper mixing

### User Interface
- **Modern PyQt6 GUI**: Clean, intuitive interface with dark theme
- **Soundboard Tab**: Visual cards for all loaded clips with play/stop/delete buttons
- **Controls Tab**: Volume sliders for master, microphone, and clips
- **Hotkeys Tab**: Easy assignment and management of keyboard shortcuts
- **Settings Tab**: Application status and configuration

## System Requirements

- **OS**: Windows, macOS, or Linux
- **Python**: 3.8 or higher
- **Audio System**: VB-Cable Virtual Audio Device (or compatible alternative)
- **RAM**: 512MB minimum
- **Disk Space**: 100MB for installation + audio files

## Installation

### 1. Clone or Download the Project
```bash
git clone <repository-url>
cd call_assistant
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install VB-Cable (Required)
- **macOS/Windows**: Download from [VB-Audio](https://vb-audio.com/Cable/)
- **Linux**: Use PulseAudio virtual sink or similar
- Follow installation instructions for your platform

## Usage

### Running the Application

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the application
python3 call_assistant.py
```

