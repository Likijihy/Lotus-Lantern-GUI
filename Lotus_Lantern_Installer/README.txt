# Lotus Lantern

Application for controlling LED strip via Bluetooth.

## Key Fixes in This Version
- Fixed LED strip control commands for compiled executable
- Improved Bluetooth reliability with multiple sending methods
- Enhanced audio capture for all Windows 11 system configurations
- Added detailed logging to troubleshoot issues

## Requirements
- Windows 10/11
- Bluetooth adapter
- Administrator rights for first run

## Installation
1. Run install_dependencies.bat as Administrator
2. Reboot your computer
3. Run Lotus Lantern.exe

## Troubleshooting
If the LED strip doesn't respond:
1. Run the application as Administrator
2. Check if your LED strip model is supported (ELK-BLEDOM/ELK-BLEDOB)
3. Ensure Bluetooth is enabled in Windows Settings
4. Check logs in %APPDATA%\Lotus Lantern\app.log for detailed errors

If music mode doesn't work:
1. Ensure "Stereo Mix" or loopback audio device is available
2. Right-click speaker icon > Sounds > Recording tab
3. Enable "Stereo Mix" or your system audio output device
4. Set it as default recording device

(c) 2025 Lotus Lantern
