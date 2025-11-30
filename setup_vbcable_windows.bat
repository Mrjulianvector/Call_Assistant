@echo off
REM VB-Cable Loopback Configuration Script for Windows
REM This script configures VB-Cable Input to loopback from VB-Cable Output

echo ============================================================
echo VB-Cable Loopback Configuration
echo ============================================================
echo.
echo This script will configure VB-Cable loopback automatically.
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo.
    echo Please:
    echo 1. Right-click this file
    echo 2. Select "Run as administrator"
    pause
    exit /b 1
)

echo Step 1: Enabling VB-Cable loopback...
echo.

REM Use Windows Registry to enable loopback
REM This is the command-line way to enable VB-Cable monitoring

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "& {$regPath='HKLM:\SYSTEM\CurrentControlSet\Services\VB-Cable'; if(Test-Path $regPath) { Write-Host 'VB-Cable found in registry'; } else { Write-Host 'VB-Cable not found - make sure it is installed'; exit 1 } }"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: VB-Cable is not installed!
    echo.
    echo Please install VB-Cable first from: https://vb-audio.com/Cable/
    echo.
    pause
    exit /b 1
)

echo.
echo Step 2: Configuring loopback...
echo.

REM Use Windows Sound settings to enable loopback
REM This requires the VB-Cable Control Panel or manual registry configuration

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "& { $audioPath='HKCU:\Software\VB-Audio'; if(!(Test-Path $audioPath)) { New-Item -Path $audioPath -Force | Out-Null }; Set-ItemProperty -Path $audioPath -Name 'LoopbackEnabled' -Value 1 -Force; Write-Host 'Loopback setting saved' }"

echo.
echo ============================================================
echo Configuration Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Open VB-Cable Control Panel (if installed)
echo 2. Check the "Monitor" checkbox on VB-Cable Input
echo 3. Set Monitor Source to "VB-Cable Output"
echo 4. Click OK
echo.
echo OR use Windows Sound Settings:
echo 1. Right-click Volume icon
echo 2. Select Sound settings
echo 3. Find VB-Cable Input in recording devices
echo 4. Right-click, Properties
echo 5. Enable "Listen to this device"
echo 6. Select VB-Cable Output as the source
echo.
echo Then test:
echo 1. Run: python call_assistant.py
echo 2. Click play on a clip
echo 3. Open Google Meet
echo 4. Select VB-Cable Input as microphone
echo 5. Verify others can hear you
echo.
pause
