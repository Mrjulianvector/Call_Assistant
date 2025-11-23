"""
Audio Device Diagnostics - Identify and troubleshoot audio device configuration
"""

import pyaudio
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioDeviceInfo:
    """Store detailed audio device information"""
    def __init__(self, index: int, name: str, max_input_channels: int,
                 max_output_channels: int, sample_rate: float):
        self.index = index
        self.name = name
        self.max_input_channels = max_input_channels
        self.max_output_channels = max_output_channels
        self.sample_rate = sample_rate

    def is_input_device(self) -> bool:
        return self.max_input_channels > 0

    def is_output_device(self) -> bool:
        return self.max_output_channels > 0

    def __repr__(self):
        return f"Device {self.index}: {self.name} (In: {self.max_input_channels}, Out: {self.max_output_channels}, {self.sample_rate}Hz)"


class AudioDiagnostics:
    """Diagnose audio device configuration and issues"""

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.devices: List[AudioDeviceInfo] = []
        self._scan_devices()

    def _scan_devices(self):
        """Scan all audio devices on the system"""
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            device = AudioDeviceInfo(
                index=i,
                name=info['name'],
                max_input_channels=info['maxInputChannels'],
                max_output_channels=info['maxOutputChannels'],
                sample_rate=info['defaultSampleRate']
            )
            self.devices.append(device)

    def list_all_devices(self) -> List[AudioDeviceInfo]:
        """Return all detected audio devices"""
        return self.devices

    def list_input_devices(self) -> List[AudioDeviceInfo]:
        """Return all input devices (microphones)"""
        return [d for d in self.devices if d.is_input_device()]

    def list_output_devices(self) -> List[AudioDeviceInfo]:
        """Return all output devices (speakers, headphones)"""
        return [d for d in self.devices if d.is_output_device()]

    def find_vbcable(self) -> Optional[AudioDeviceInfo]:
        """Find VB-Cable device"""
        for device in self.devices:
            if "vb" in device.name.lower() and "cable" in device.name.lower():
                return device
        return None

    def find_microphone(self) -> Optional[AudioDeviceInfo]:
        """Find dedicated microphone device"""
        for device in self.list_input_devices():
            if "microphone" in device.name.lower():
                return device
        return None

    def find_builtin_speakers(self) -> Optional[AudioDeviceInfo]:
        """Find built-in speakers (prefer Mac mini Speakers over HDMI)"""
        output_devices = self.list_output_devices()

        # First preference: built-in speakers
        for device in output_devices:
            name_lower = device.name.lower()
            if "mac mini speakers" in name_lower or "speaker" in name_lower:
                return device

        # Second preference: headphones or AirPods
        for device in output_devices:
            name_lower = device.name.lower()
            if "headphone" in name_lower or "airpods" in name_lower:
                return device

        # Last resort: any output device except HDMI
        for device in output_devices:
            if "hdmi" not in device.name.lower():
                return device

        return None

    def get_default_input(self) -> Optional[AudioDeviceInfo]:
        """Get system default input device"""
        try:
            default_idx = self.p.get_default_input_device_info()['index']
            return next((d for d in self.devices if d.index == default_idx), None)
        except OSError:
            return None

    def get_default_output(self) -> Optional[AudioDeviceInfo]:
        """Get system default output device"""
        try:
            default_idx = self.p.get_default_output_device_info()['index']
            return next((d for d in self.devices if d.index == default_idx), None)
        except OSError:
            return None

    def diagnose(self) -> Dict:
        """Run full diagnostics and return report"""
        report = {
            "all_devices": self.list_all_devices(),
            "input_devices": self.list_input_devices(),
            "output_devices": self.list_output_devices(),
            "vbcable": self.find_vbcable(),
            "microphone": self.find_microphone(),
            "builtin_speakers": self.find_builtin_speakers(),
            "default_input": self.get_default_input(),
            "default_output": self.get_default_output(),
        }
        return report

    def print_report(self):
        """Print a formatted diagnostic report"""
        report = self.diagnose()

        print("\n" + "="*60)
        print("AUDIO DEVICE DIAGNOSTICS REPORT")
        print("="*60 + "\n")

        print("ALL DEVICES:")
        for device in report['all_devices']:
            print(f"  {device}")

        print("\nINPUT DEVICES (Microphones):")
        if report['input_devices']:
            for device in report['input_devices']:
                print(f"  ✓ {device}")
        else:
            print("  ✗ NO INPUT DEVICES FOUND")

        print("\nOUTPUT DEVICES (Speakers/Headphones):")
        if report['output_devices']:
            for device in report['output_devices']:
                print(f"  ✓ {device}")
        else:
            print("  ✗ NO OUTPUT DEVICES FOUND")

        print("\nDEVICE DETECTION:")
        vb = report['vbcable']
        print(f"  VB-Cable: {'✓ FOUND' if vb else '✗ NOT FOUND'} {f'(Device {vb.index}: {vb.name})' if vb else ''}")

        mic = report['microphone']
        print(f"  Microphone: {'✓ FOUND' if mic else '✗ NOT FOUND'} {f'(Device {mic.index}: {mic.name})' if mic else ''}")

        speakers = report['builtin_speakers']
        print(f"  Speakers: {'✓ FOUND' if speakers else '✗ NOT FOUND'} {f'(Device {speakers.index}: {speakers.name})' if speakers else ''}")

        print("\nDEFAULT DEVICES:")
        default_in = report['default_input']
        print(f"  Input: {default_in.name if default_in else 'NONE'}")

        default_out = report['default_output']
        print(f"  Output: {default_out.name if default_out else 'NONE'}")

        print("\nRECOMMENDATIONS:")
        issues = []

        if not report['microphone']:
            issues.append("  ⚠ NO DEDICATED MICROPHONE FOUND - Connect a USB microphone or enable system microphone")

        if default_in and default_in.name and "vb-cable" in default_in.name.lower():
            issues.append("  ⚠ DEFAULT INPUT IS VB-CABLE - This should be your microphone, not VB-Cable")

        if not speakers or ("hdmi" in speakers.name.lower()):
            issues.append("  ⚠ WRONG SPEAKER OUTPUT - Should use Mac mini Speakers, not HDMI")

        if issues:
            for issue in issues:
                print(issue)
        else:
            print("  ✓ All audio devices appear to be configured correctly")

        print("\n" + "="*60 + "\n")

    def cleanup(self):
        """Clean up PyAudio instance"""
        self.p.terminate()


if __name__ == "__main__":
    diagnostics = AudioDiagnostics()
    diagnostics.print_report()
    diagnostics.cleanup()
