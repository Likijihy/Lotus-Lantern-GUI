@echo off
echo Установка системных зависимостей...
start /wait vcredist_x64.exe /install /quiet /norestart
echo Готово! Теперь можно запускать Lotus Lantern.
pause