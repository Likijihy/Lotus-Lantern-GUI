# 🌸 Lotus Lantern

A modern Python desktop app to control BLE LED strips wirelessly.  
Simple, dark-themed UI with system tray support, persistent settings, and effect previews.  
Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) and [Bleak](https://github.com/hbldh/bleak).

![UI Screenshot](https://github.com/Likijihy/Lotus-Lantern-GUI/blob/main/screenshots/ui_main.png?raw=true)

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

1. Install Python 3.14+  
2. Clone this repo:

```bash
git clone https://github.com/FreeAkrep/Lotus-Lantern-GUI
cd Lotus-Lantern-GUI
```
Run "Build.ps1!" as administrator
If you did not have python 3.14+ installed, the program will ask you to restart the script file.
After the build, you will get a new directory **Lotus_Lantern_Installer**,
which will contain the following files:
-  **Lotus Lantern.exe**,
-  **README.txt**,
-  **install_dependencies.bat** 

# 🏆 Credits
Main Developer: FreeAkrep
Mod Developere: Likijihy

BLE Command Logic Inspired By:

  [lorgan3/lotus-lantern-client)](https://github.com/lorgan3/lotus-lantern-client)

  [TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller](https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller)

BLE Library: [Bleak](https://github.com/hbldh/bleak)

UI Framework: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

Thanks to the open-source community for making this possible!

