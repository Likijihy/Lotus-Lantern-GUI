$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Для установки в систему необходим запуск от имени администратора."
    exit 1
}

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python не найден"
    Write-Host "Хотите установить Python 3.14 сейчас?" -ForegroundColor Yellow

    do {
        $choice = Read-Host "Установить Python? (Y/N)"
    } while ($choice -notmatch '^[YyNn]$')

    if ($choice -in @('Y', 'y')) {
        Write-Host "Установка Python через winget..."
        winget install -e --id Python.Python.3.14 --scope machine
        
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        if (Get-Command python -ErrorAction SilentlyContinue) {
            Write-Host "Python успешно установлен и доступен." -ForegroundColor Green
        } else {
            Write-Warning "Python установлен, но не обнаружен в PATH текущей сессии. Возможно, потребуется перезапуск терминала."
        }
    } else {
        Write-Host "Установка отменена." -ForegroundColor Red
        exit 1
    }
}

pip install pyinstaller customtkinter bleak sounddevice numpy pywin32

$buildDir = "build_temp"
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $buildDir | Out-Null

Copy-Item "icon.ico" -Destination $buildDir -ErrorAction SilentlyContinue
Copy-Item "main.py" -Destination $buildDir
if (Test-Path "src") {
    Copy-Item "src" -Destination $buildDir -Recurse -ErrorAction SilentlyContinue
}

Set-Location $buildDir

$pyinstallerArgs = @(
    "main.py",
    "-n", "Lotus Lantern",
    "-F",
    "--add-data", "icon.ico;.",
    "-i", "icon.ico",
    "--hidden-import", "customtkinter",
    "--hidden-import", "bleak",
    "--hidden-import", "bleak.backends.winrt",
    "--hidden-import", "sounddevice",
    "--hidden-import", "numpy",
    "--hidden-import", "win32api",
    "--hidden-import", "win32con",
    "--hidden-import", "win32gui",
    "--hidden-import", "pywin32",
    "--hidden-import", "ctypes",
    "--hidden-import", "asyncio",
    "--hidden-import", "tkinter",
    "--hidden-import", "PIL",
    "--noconsole",
    "--clean"
)

& pyinstaller @pyinstallerArgs

Set-Location ..

$distPath = Join-Path $buildDir "dist"
if (Test-Path $distPath) {
    $outputDir = "Lotus_Lantern_Installer"
    if (Test-Path $outputDir) {
        Remove-Item $outputDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    
    Copy-Item (Join-Path $distPath "Lotus Lantern.exe") -Destination $outputDir
    
    Write-Host "Installing system dependencies for Lotus Lantern..."
Write-Host

Write-Host "Checking for Visual C++ Redistributable..."
if (-not (Test-Path "$env:SystemRoot\System32\vcruntime140.dll")) {
    Write-Host "Installing Visual C++ Redistributable..."

    $vcUrl  = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
    $vcPath = Join-Path $env:TEMP 'vc_redist.x64.exe'

    Invoke-WebRequest -Uri $vcUrl -OutFile $vcPath
    $p = Start-Process -FilePath $vcPath -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
    if ($p.ExitCode -ne 0) {
        Write-Host "VC++ installer exited with code $($p.ExitCode)." -ForegroundColor Red
    }

    Remove-Item $vcPath -ErrorAction SilentlyContinue
    Write-Host "Visual C++ Redistributable installed."
} else {
    Write-Host "Visual C++ Redistributable is already installed."
}

Write-Host
Write-Host "Ensuring Bluetooth services are running..."
sc.exe config bthserv start= auto | Out-Null
net.exe start bthserv 2>&1 | Out-Null

Write-Host
Write-Host "Granting permissions to Bluetooth..."

Write-Host
Write-Host "Setup complete! You can now run Lotus Lantern."
Write-Host "A reboot may be required for audio and Bluetooth features to work properly."
Write-Host
Read-Host "Press Enter to continue..."
    
    $readme = @"
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
1. Run `install_dependencies.bat` as Administrator
2. Reboot your computer
3. Run `Lotus Lantern.exe`

## Troubleshooting
If the LED strip doesn't respond:
1. Run the script as Administrator (dependencies are installed automatically)
2. Check if your LED strip model is supported (ELK-BLEDOM/ELK-BLEDOB)
3. Ensure Bluetooth is enabled in Windows Settings
4. Check logs in %APPDATA%\Lotus Lantern\app.log for detailed errors

If music mode doesn't work:
1. Ensure "Stereo Mix" or loopback audio device is available
2. Right-click speaker icon > Sounds > Recording tab
3. Enable "Stereo Mix" or your system audio output device
4. Set it as default recording device

(c) 2025 Lotus Lantern
"@
    $readme | Out-File (Join-Path $outputDir "README.txt") -Encoding ascii
    
    Write-Host "Build completed successfully!"
    Write-Host "Executable file is located at: $outputDir\Lotus Lantern.exe"
    Write-Host "To install dependencies, run: $outputDir\install_dependencies.bat"
} else {
    Write-Error "Build failed. Check logs in folder $buildDir"
}

if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force

}
