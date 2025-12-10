import asyncio
import customtkinter as ctk
from bleak import BleakClient, BleakScanner
from threading import Thread
from tkinter import colorchooser
import json
import os
import logging
import time
import numpy as np
import tempfile
import atexit
import shutil
import sys
import win32api
import win32con
import win32gui

import ctypes
from ctypes import wintypes

from src.ble_commands import (
    send_turn_on, send_turn_off,
    send_color, send_brightness,
    send_mode, send_effect_speed
)
from src.audio_analyzer import AudioAnalyzer

APP_NAME = "Lotus Lantern"
APPDATA_PATH = os.path.join(os.environ["APPDATA"], APP_NAME)
os.makedirs(APPDATA_PATH, exist_ok=True)

CONFIG_PATH = os.path.join(APPDATA_PATH, "config.json")
LOG_PATH = os.path.join(APPDATA_PATH, "app.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


class BLEController:
    def __init__(self, command_callback=None):
        self.client = None
        self.command_queue = asyncio.Queue()
        self._connected_device_info = None
        self._command_callback = command_callback

    async def run(self):
        while True:
            try:
                cmd, args = await self.command_queue.get()
                if cmd == "connect":
                    await self._connect(*args)
                elif cmd == "disconnect":
                    await self._disconnect()
                elif cmd == "send":
                    await self._send_command(*args)
                self.command_queue.task_done()
            except Exception as e:
                logging.error(f"BLEController error: {e}")
                if self._command_callback:
                    self._command_callback("error", str(e))

    async def _connect(self, device, on_success):
        try:
            self.client = BleakClient(device)
            await self.client.connect()
            self._connected_device_info = device.name or device.address
            logging.info(f"Connected to {self._connected_device_info}")
            if self._command_callback:
                self._command_callback("connected", self._connected_device_info)
            if on_success:
                on_success()
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            if self._command_callback:
                self._command_callback("error", str(e))

    async def _disconnect(self):
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.client = None
            self._connected_device_info = None
            if self._command_callback:
                self._command_callback("disconnected", None)
        except Exception as e:
            logging.error(f"Disconnect error: {e}")

    async def _send_command(self, func, *args):
        if self.client and self.client.is_connected:
            try:
                await func(self.client, *args)
            except Exception as e:
                logging.error(f"BLE send error: {e}")
                if self._command_callback:
                    self._command_callback("error", str(e))

    def queue_connect(self, device, on_success=None):
        asyncio.run_coroutine_threadsafe(
            self.command_queue.put(("connect", (device, on_success))), loop
        )

    def queue_disconnect(self):
        asyncio.run_coroutine_threadsafe(
            self.command_queue.put(("disconnect", ())), loop
        )

    def queue_send(self, func, *args):
        asyncio.run_coroutine_threadsafe(
            self.command_queue.put(("send", (func, *args))), loop
        )

    def is_connected(self):
        return self.client is not None and self.client.is_connected

    def get_device_name(self):
        return self._connected_device_info or "Неизвестно"


class BLEApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lotus Lantern")
        self.geometry("420x820")
        self.resizable(False, False)

        icon_path = self.get_icon_path()
        if icon_path:
            self.iconbitmap(icon_path)

        self.current_color = (0, 255, 0)
        self.current_brightness = 128
        self.current_mode = "Статический"
        self.current_effect_speed = 50
        self.sensitivity = 50
        self.color_algorithm = "Общий вайб"
        self.devices = []
        self.music_mode_active = False
        self.last_music_color = (0, 0, 0)
        self.last_send_time = 0
        self.color_history = []
        self.hue_phase = 0
        self.pulse_phase = 0
        self.last_energy = 0

        self.audio_analyzer = AudioAnalyzer()
        self.ble = BLEController(command_callback=self._on_ble_event)

        self.load_settings()
        self.create_scan_ui()

        Thread(target=self._run_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.ble.run(), loop)
        self._register_shutdown_handler()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _run_loop(self):
        loop.run_forever()
        
    def get_icon_path(self):
            if getattr(sys, 'frozen', False):
                icon_data = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                icon_src = os.path.join(icon_data, 'icon.ico')
                if os.path.exists(icon_src):
                    temp_dir = tempfile.mkdtemp()
                    icon_dst = os.path.join(temp_dir, 'icon.ico')
                    shutil.copy2(icon_src, icon_dst)
                    atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
                    return icon_dst
            else:
                if os.path.exists("icon.ico"):
                    return "icon.ico"
            return None
        
    def on_closing(self):
        self.save_settings()
        self.stop_music_mode()
        self.audio_analyzer.close()
        self.destroy()


    def _register_shutdown_handler(self):
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._shutdown_window_proc
            wc.lpszClassName = "LotusShutdownWindowClass"
            wc.hInstance = win32api.GetModuleHandle(None)
            class_atom = win32gui.RegisterClass(wc)
            
            self.shutdown_hwnd = win32gui.CreateWindow(
                class_atom, "LotusShutdownWindow", 
                0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
            )
            
            win32api.SetConsoleCtrlHandler(self._console_handler, True)
            
            logging.info("Shutdown handler registered")
        except Exception as e:
            logging.error(f"Failed to register shutdown handler: {e}")
            
    def _shutdown_window_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_QUERYENDSESSION or msg == win32con.WM_ENDSESSION:
            # Выключаем ленту при выключении системы
            self._safe_turn_off_on_shutdown()
            return 1  # Разрешаем выключение
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    
    def _console_handler(self, ctrl_type):
        if ctrl_type in [win32con.CTRL_SHUTDOWN_EVENT, win32con.CTRL_CLOSE_EVENT]:
            self._safe_turn_off_on_shutdown()
            return True  # Обработали событие
        return False


    def _safe_turn_off_on_shutdown(self):
        if self.ble.is_connected():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._emergency_turn_off(), 
                    loop
                )
                logging.info("Emergency turn off command sent on Windows shutdown")
                
                time.sleep(0.3)
            except Exception as e:
                logging.error(f"Emergency shutdown failed: {e}")
                
    async def _emergency_turn_off(self):
        try:
            await send_turn_off(self.ble.client)
            command = bytearray([0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef])
            
            if self.ble.client and self.ble.client.is_connected:
                for char in self.ble.client.services.characteristics.values():
                    try:
                        await self.ble.client.write_gatt_char(char.uuid, command)
                        break
                    except:
                        continue
        except Exception as e:
            logging.error(f"Direct emergency turn off failed: {e}")

    def _on_ble_event(self, event_type, data):
        if event_type == "connected":
            self.after(0, lambda: self._on_connected(data))
        elif event_type == "disconnected":
            self.after(0, self._on_disconnected)
        elif event_type == "error":
            self.after(0, lambda: self._show_error(data))

    def _show_error(self, msg):
        try:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", msg)
        except Exception:
            pass

    def _on_connected(self, device_name):
        self.create_control_ui()
        self.status_device.configure(text=device_name)
        self.status_indicator.configure(fg_color="green")

    def _on_disconnected(self):
        self.status_device.configure(text="Не подключено")
        self.status_indicator.configure(fg_color="red")
        self.create_scan_ui()

    def clear_window(self):
        for widget in self.winfo_children():
            try:
                widget.destroy()
            except:
                pass

    def create_scan_ui(self):
        self.clear_window()

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=(15, 5))
        ctk.CTkLabel(title_frame, text="Lotus Lantern", font=("Arial", 22, "bold")).pack()

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(pady=(0, 15))
        self.status_indicator = ctk.CTkFrame(status_frame, width=12, height=12, corner_radius=6, fg_color="red")
        self.status_indicator.pack(side="left", padx=(0, 10))
        self.status_device = ctk.CTkLabel(status_frame, text="Не подключено", text_color="#AAAAAA", font=("Arial", 13))
        self.status_device.pack(side="left")

        self.scan_btn = ctk.CTkButton(
            self, text="🔄 Сканировать",
            font=("Arial", 14),
            height=40,
            fg_color="#3b8ed0",
            hover_color="#36719f",
            command=self.scan_devices
        )
        self.scan_btn.pack(pady=12, padx=30, fill="x")

        self.device_menu = ctk.CTkOptionMenu(
            self,
            values=["Нет устройств"],
            font=("Arial", 13),
            dropdown_font=("Arial", 13)
        )
        self.device_menu.pack(pady=12, padx=30, fill="x")

        self.connect_btn = ctk.CTkButton(
            self, text="Подключиться",
            font=("Arial", 14),
            height=40,
            state="disabled",
            fg_color="#5d8aa8",
            hover_color="#4a6b82",
            command=self.connect_device
        )
        self.connect_btn.pack(pady=12, padx=30, fill="x")

    def create_control_ui(self):
        self.clear_window()

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=(15, 5))
        ctk.CTkLabel(title_frame, text="Lotus Lantern", font=("Arial", 22, "bold")).pack()

        status_frame = ctk.CTkFrame(self, fg_color="#1c1c1c", corner_radius=10)
        status_frame.pack(pady=(0, 15), padx=20, fill="x")
        ctk.CTkLabel(status_frame, text="Подключено к:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.status_device = ctk.CTkLabel(status_frame, text="...", font=("Arial", 12))
        self.status_device.pack(side="left")
        self.status_indicator = ctk.CTkFrame(status_frame, width=10, height=10, corner_radius=5, fg_color="green")
        self.status_indicator.pack(side="right", padx=10)

        ctk.CTkButton(
            self, text="Отключиться",
            fg_color="#9b5de5",
            hover_color="#7a4bc0",
            height=35,
            command=self.disconnect_device
        ).pack(pady=(5, 15), padx=30, fill="x")

        power_frame = ctk.CTkFrame(self, fg_color="transparent")
        power_frame.pack(pady=(0, 15))
        ctk.CTkButton(
            power_frame, text="✔️ ВКЛ",
            fg_color="#00cc66",
            hover_color="#00aa55",
            width=100,
            height=40,
            font=("Arial", 14, "bold"),
            command=self.turn_on
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            power_frame, text="✖️ ОТКЛ",
            fg_color="#ff4d4d",
            hover_color="#cc3333",
            width=100,
            height=40,
            font=("Arial", 14, "bold"),
            command=self.turn_off
        ).pack(side="left", padx=5)

        color_frame = ctk.CTkFrame(self, fg_color="transparent")
        color_frame.pack(pady=(0, 15))
        ctk.CTkLabel(color_frame, text="Палитра цветов", font=("Arial", 14)).pack()
        self.color_preview = ctk.CTkFrame(color_frame, width=120, height=30, corner_radius=8)
        self.color_preview.pack(pady=8)
        self.update_color_preview()
        ctk.CTkButton(
            color_frame, text="🎨 Выбрать цвет",
            fg_color="#3b8ed0",
            hover_color="#36719f",
            command=self.choose_color
        ).pack(pady=5)

        self.create_slider_with_value(
            "Яркость", 0, 255, self.current_brightness, self.change_brightness, "brightness_value"
        )

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(mode_frame, text="Режим подсветки", font=("Arial", 14)).pack()
        self.mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            values=["Статический", "Мерцание", "Переливание", "Радуга", "Стробы", "Волна", "Музыкальный"],
            command=self.set_mode,
            font=("Arial", 13),
            dropdown_font=("Arial", 13)
        )
        self.mode_menu.set(self.current_mode)
        self.mode_menu.pack(pady=5, fill="x")

        self.create_slider_with_value(
            "Скорость эффектов", 1, 100, self.current_effect_speed, self.change_effect_speed, "effect_speed_value"
        )

        self.music_settings_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        self._toggle_music_settings()

    def create_slider_with_value(self, label, min_val, max_val, default, command, attr_name):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame, text=label, font=("Arial", 14)).pack(anchor="w", padx=5)

        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(5, 0))

        slider = ctk.CTkSlider(
            slider_frame,
            from_=min_val,
            to=max_val,
            number_of_steps=max_val - min_val,
            command=command
        )
        slider.set(default)
        slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        value_label = ctk.CTkLabel(slider_frame, text=str(int(default)), width=30)
        value_label.pack(side="right")
        setattr(self, attr_name, value_label)

    def _toggle_music_settings(self):
        if self.current_mode == "Музыкальный":
            self.music_settings_frame.pack(pady=10, padx=20, fill="x")
            self.create_music_sliders()
        else:
            self.music_settings_frame.pack_forget()

    def create_music_sliders(self):
        for widget in self.music_settings_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.music_settings_frame, text="🎵 Настройки музыкального режима", font=("Arial", 14, "bold")).pack(pady=(10, 5))

        sens_frame = ctk.CTkFrame(self.music_settings_frame, fg_color="transparent")
        sens_frame.pack(pady=5, padx=10, fill="x")
        slider = ctk.CTkSlider(sens_frame, from_=10, to=100, command=self.change_sensitivity)
        slider.set(self.sensitivity)
        slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.sensitivity_value = ctk.CTkLabel(sens_frame, text=str(int(self.sensitivity)), width=30)
        self.sensitivity_value.pack(side="right")

        algo_frame = ctk.CTkFrame(self.music_settings_frame, fg_color="transparent")
        algo_frame.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(algo_frame, text="Цветовой алгоритм:", font=("Arial", 12)).pack(anchor="w")
        self.algorithm_menu = ctk.CTkOptionMenu(
            algo_frame,
            values=["Частотный RGB", "Общий вайб", "Спектр музыки", "Пульсирующие волны", "Огненный эквалайзер"],
            command=self.change_color_algorithm,
            font=("Arial", 12),
            dropdown_font=("Arial", 12)
        )
        self.algorithm_menu.set(self.color_algorithm)
        self.algorithm_menu.pack(fill="x", pady=(5, 0))

        ctk.CTkLabel(self.music_settings_frame, text="", height=10).pack()

    def change_sensitivity(self, value):
        self.sensitivity = int(value)
        self.sensitivity_value.configure(text=str(int(value)))

    def change_color_algorithm(self, algorithm):
        self.color_algorithm = algorithm

    def set_mode(self, mode):
        self.current_mode = mode
        self._toggle_music_settings()
        if mode == "Музыкальный":
            self.start_music_mode()
        else:
            self.stop_music_mode()
            self.ble.queue_send(send_mode, mode)

    def scan_devices(self):
        self.device_menu.configure(values=["Сканирование..."])
        asyncio.run_coroutine_threadsafe(self._scan_async(), loop)

    async def _scan_async(self):
        try:
            self.devices = await BleakScanner.discover()
            names = [d.name or d.address for d in self.devices] or ["Нет устройств"]
            self.device_menu.configure(values=names)
            self.device_menu.set(names[0])
            self.connect_btn.configure(state="normal" if self.devices else "disabled")
        except Exception as e:
            logging.error(f"Scan failed: {e}")
            self.after(0, lambda: self._show_error(f"Сканирование не удалось: {e}"))

    def connect_device(self):
        try:
            values = self.device_menu.cget("values")
            name = self.device_menu.get()
            if name in values:
                index = values.index(name)
                if index < len(self.devices):
                    device = self.devices[index]
                    self.ble.queue_connect(device)
        except Exception as e:
            logging.error(f"Connect error: {e}")

    def disconnect_device(self):
        self.save_settings()
        self.stop_music_mode()
        self.ble.queue_disconnect()

    def turn_on(self):
        self.ble.queue_send(send_turn_on)

    def turn_off(self):
        self.ble.queue_send(send_turn_off)

    def choose_color(self):
        color = colorchooser.askcolor()[0]
        if color:
            self.current_color = tuple(int(c) for c in color)
            self.update_color_preview()
            self.ble.queue_send(send_color, self.current_color)

    def update_color_preview(self):
        hex_color = self.rgb_to_hex(self.current_color)
        self.color_preview.configure(fg_color=hex_color)

    def change_brightness(self, value):
        self.current_brightness = int(value)
        self.brightness_value.configure(text=str(int(value)))
        self.ble.queue_send(send_brightness, self.current_brightness)

    def change_effect_speed(self, value):
        self.current_effect_speed = int(value)
        self.effect_speed_value.configure(text=str(int(value)))
        self.ble.queue_send(send_effect_speed, self.current_effect_speed)

    def start_music_mode(self):
        if not self.music_mode_active:
            self.turn_on()
            self.ble.queue_send(send_mode, "Статический")
            self.ble.queue_send(send_color, (100, 100, 100))

            self.audio_analyzer.set_frequency_callback(self.on_frequency_data)
            success = self.audio_analyzer.start_capture()
            if not success:
                self.music_mode_active = False
                self.after(0, lambda: self._show_error(
                    "Не удалось запустить захват системного звука.\n\n"
                    "Возможные решения:\n"
                    "1. Проверьте наличие устройства 'Stereo Mix'\n"
                    "2. Включите стерео микшер в настройках звука\n"
                    "3. Проверьте права доступа к микрофону"
                ))
            else:
                self.music_mode_active = True

    def stop_music_mode(self):
        if self.music_mode_active:
            self.music_mode_active = False
            self.audio_analyzer.stop_capture()

    def on_frequency_data(self, low_freq, mid_freq, high_freq):
        if not self.music_mode_active or not self.ble.is_connected():
            return
        try:
            if self.color_algorithm == "Частотный RGB":
                color = self.algorithm_frequency_rgb(low_freq, mid_freq, high_freq)
            elif self.color_algorithm == "Общий вайб":
                color = self.algorithm_energy_based(low_freq, mid_freq, high_freq)
            elif self.color_algorithm == "Спектр музыки":
                color = self.algorithm_music_spectrum(low_freq, mid_freq, high_freq)
            elif self.color_algorithm == "Пульсирующие волны":
                color = self.algorithm_pulse_waves(low_freq, mid_freq, high_freq)
            elif self.color_algorithm == "Огненный эквалайзер":
                color = self.algorithm_fire_equalizer(low_freq, mid_freq, high_freq)
            else:
                color = self.algorithm_energy_based(low_freq, mid_freq, high_freq)

            self.color_history.append(color)
            if len(self.color_history) > 3:
                self.color_history.pop(0)
            avg_r = sum(c[0] for c in self.color_history) // len(self.color_history)
            avg_g = sum(c[1] for c in self.color_history) // len(self.color_history)
            avg_b = sum(c[2] for c in self.color_history) // len(self.color_history)
            color = (avg_r, avg_g, avg_b)
            self.last_music_color = color

            current_time = time.time()
            if current_time - self.last_send_time > 0.05:
                self.ble.queue_send(send_color, color)
                self.last_send_time = current_time
        except Exception as e:
            logging.error(f"Audio error: {e}")

    def algorithm_frequency_rgb(self, low_freq, mid_freq, high_freq):
        sensitivity = self.sensitivity / 50.0
        r = int(np.clip(low_freq * sensitivity * 15, 0, 255))
        g = int(np.clip(mid_freq * sensitivity * 12, 0, 255))
        b = int(np.clip(high_freq * sensitivity * 10, 0, 255))
        max_val = max(r, g, b)
        if max_val > 0 and max_val < 100:
            scale = 200 / max_val
            r = min(255, int(r * scale))
            g = min(255, int(g * scale))
            b = min(255, int(b * scale))
        return (r, g, b)

    def algorithm_energy_based(self, low_freq, mid_freq, high_freq):
        sensitivity = self.sensitivity / 50.0
        total_energy = (low_freq + mid_freq + high_freq) * sensitivity
        total = low_freq + mid_freq + high_freq + 0.001
        low_ratio = low_freq / total
        mid_ratio = mid_freq / total
        high_ratio = high_freq / total
        if low_ratio > 0.6:
            base_hue = 0
        elif mid_ratio > 0.6:
            base_hue = 120
        elif high_ratio > 0.6:
            base_hue = 240
        else:
            base_hue = (low_ratio * 0 + mid_ratio * 120 + high_ratio * 240) % 360
        self.hue_phase = (self.hue_phase + total_energy * 0.1) % 360
        hue = (base_hue + self.hue_phase) % 360
        saturation = min(1.0, total_energy * 0.02)
        value = min(1.0, total_energy * 0.01)
        return self.hsv_to_rgb(hue, saturation, value)

    def algorithm_music_spectrum(self, low_freq, mid_freq, high_freq):
        sensitivity = self.sensitivity / 50.0
        bass_energy = low_freq * sensitivity * 20
        melody_energy = mid_freq * sensitivity * 15
        treble_energy = high_freq * sensitivity * 10
        is_bass_heavy = bass_energy > melody_energy * 1.5
        is_treble_heavy = treble_energy > melody_energy * 1.5
        if is_bass_heavy:
            r, g, b = bass_energy * 2, melody_energy, treble_energy * 0.5
        elif is_treble_heavy:
            r, g, b = bass_energy * 0.5, melody_energy, treble_energy * 2
        else:
            r, g, b = bass_energy * 1.2, melody_energy * 1.5, treble_energy * 1.2
        r = int(255 * (min(r, 255) / 255) ** 0.8)
        g = int(255 * (min(g, 255) / 255) ** 0.7)
        b = int(255 * (min(b, 255) / 255) ** 0.9)
        return (r, g, b)

    def algorithm_pulse_waves(self, low_freq, mid_freq, high_freq):
        sensitivity = self.sensitivity / 50.0
        total_energy = (low_freq + mid_freq + high_freq) * sensitivity
        energy_change = abs(total_energy - self.last_energy)
        self.last_energy = total_energy
        if energy_change > 5:
            self.pulse_phase = (self.pulse_phase + 30) % 360
        self.pulse_phase = (self.pulse_phase + 0.5) % 360
        hue = (self.pulse_phase + low_freq * 2) % 360
        saturation = min(1.0, 0.7 + mid_freq * 0.01)
        value = min(1.0, 0.3 + total_energy * 0.015)
        if energy_change > 10:
            value = min(1.0, value * 1.5)
        return self.hsv_to_rgb(hue, saturation, value)

    def algorithm_fire_equalizer(self, low_freq, mid_freq, high_freq):
        sensitivity = self.sensitivity / 50.0
        fire_colors = [(20,0,0), (50,0,0), (100,10,0), (150,30,0), (200,60,0), (255,100,0), (255,150,50)]
        total_energy = (low_freq * 0.5 + mid_freq * 0.3 + high_freq * 0.2) * sensitivity
        temperature = min(len(fire_colors) - 1, int(total_energy * 0.5))
        flicker = high_freq * 20
        base_color = fire_colors[temperature]
        r = min(255, base_color[0] + int(flicker))
        g = min(255, base_color[1] + int(flicker * 0.5))
        b = min(255, base_color[2] + int(flicker * 0.2))
        return (r, g, b)

    def hsv_to_rgb(self, h, s, v):
        h = h % 360
        s = max(0, min(1, s))
        v = max(0, min(1, v))
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if h < 60: r, g, b = c, x, 0
        elif h < 120: r, g, b = x, c, 0
        elif h < 180: r, g, b = 0, c, x
        elif h < 240: r, g, b = 0, x, c
        elif h < 300: r, g, b = x, 0, c
        else: r, g, b = c, 0, x
        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

    def rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def save_settings(self):
        config = {
            "color": self.current_color,
            "brightness": self.current_brightness,
            "mode": self.current_mode,
            "effect_speed": self.current_effect_speed,
            "sensitivity": self.sensitivity,
            "color_algorithm": self.color_algorithm
        }
        try:
            with open(CONFIG_PATH, "w", encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def load_settings(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding='utf-8') as f:
                config = json.load(f)
                self.current_color = tuple(config.get("color", (0, 255, 0)))
                self.current_brightness = config.get("brightness", 128)
                self.current_mode = config.get("mode", "Статический")
                self.current_effect_speed = config.get("effect_speed", 50)
                self.sensitivity = config.get("sensitivity", 50)
                self.color_algorithm = config.get("color_algorithm", "Общий вайб")
        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    def destroy(self):
        self.save_settings()
        self.stop_music_mode()
        self.audio_analyzer.close()
        super().destroy()



if __name__ == "__main__":
    app = BLEApp()
    app.mainloop()