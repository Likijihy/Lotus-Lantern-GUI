# 🌸 Lotus Lantern

A modern Python desktop app to control BLE LED strips wirelessly.  
Simple, dark-themed UI with system tray support, persistent settings, and effect previews.  
Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and [Bleak](https://github.com/hbldh/bleak).

![UI Screenshot](https://github.com/Likijihy/Lotus-Lantern-win/blob/main/screenshots/ui_main.png?raw=true)

---

## ✨ Features

- 🔌 Connect to BLE-enabled LED controllers
- 🎨 Change LED colors with color picker or tray presets
- 💡 Adjust brightness (scaled 1–5)
- 🎭 Switch between lighting modes: Static, Fade, Blink, Rainbow, Strobe, Wave
- ⚡ Adjust effect speed
- 💾 Remembers last settings on next launch
- 🔧 Simple JSON-based config

---

## 📦 Installation (Windows)

### Option 1: Run from Source (Recommended)

1. Install Python 3.10+  
2. Clone this repo:

```bash
git clone https://github.com/FreeAkrep/Lotus-Lantern-GUI
cd Lotus-Lantern-GUI
pip install -r requirements.txt
python main.py
```
# 🪟 Windows Build

Build the standalone .exe using PyInstaller
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --icon=icon.ico main.py
```
The built .exe will be in the dist/ folder.

# 🐧 Linux Build
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed main.py
```
You may need to install Bluetooth development headers:
```bash
sudo apt install libbluetooth-dev
```
💡 Ensure you have permission to access BLE devices (add user to the bluetooth group or run with sudo).
# 🏆 Credits
Main Developer: FreeAkrep

BLE Command Logic Inspired By:

  [lorgan3/lotus-lantern-client)](https://github.com/lorgan3/lotus-lantern-client)

  [TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller](https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller)

BLE Library: [Bleak](https://github.com/hbldh/bleak)

UI Framework: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

Thanks to the open-source community for making this possible!

