@echo off
echo Installing system dependencies for Lotus Lantern...
echo.

echo Checking for Visual C++ Redistributable...
if not exist "%SystemRoot%\System32\vcruntime140.dll" (
    echo Installing Visual C++ Redistributable...
    powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile 'vc_redist.x64.exe'"
    start /wait vc_redist.x64.exe /install /quiet /norestart
    del vc_redist.x64.exe
    echo Visual C++ Redistributable installed.
) else (
    echo Visual C++ Redistributable is already installed.
)
    
echo.
echo Ensuring Bluetooth services are running...
sc config bthserv start= auto
net start bthserv >nul 2>&1

echo.
echo Granting permissions to Bluetooth...
powershell -Command "Add-AppxPackage -Register 'C:\Windows\System32\BluetoothAPIs.dll' -ForceApplicationShutdown" >nul 2>&1

echo.
echo Setup complete! You can now run Lotus Lantern.
echo A reboot may be required for audio and Bluetooth features to work properly.
echo.
pause
