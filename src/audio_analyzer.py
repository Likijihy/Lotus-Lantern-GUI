import sounddevice as sd
import numpy as np
import threading
import time
from collections import deque

class AudioAnalyzer:
    def __init__(self, sample_rate=44100, chunk_size=2048):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_running = False
        self.stream = None
        self.volume_callback = None
        self.frequency_callback = None
        
        self.volume_history = deque(maxlen=5)
        self.frequency_history = deque(maxlen=5)
        
        self.last_volume = 0
        self.last_frequencies = (0, 0, 0)
        self.callback_count = 0

    def list_audio_devices(self):
        devices = sd.query_devices()

    def find_loopback_device(self):
        devices = sd.query_devices()
        
        loopback_keywords = [
            'stereo mix', 'loopback', 'what u hear', 
            'stereo микшер', 'mix', 'микшер',
            'выход', 'output', 'system', 'speakers',
            'динамики'
        ]
        
        for i, device in enumerate(devices):
            device_name = device['name'].lower()
            if any(keyword in device_name for keyword in loopback_keywords):
                if device['max_input_channels'] > 0:
                    return i
        
        for i, device in enumerate(devices):
            device_name = device['name'].lower()
            if any(mic_word in device_name for mic_word in ['microphone', 'mic', 'микрофон']):
                continue
                
            if device['max_input_channels'] > 0:
                if 'input' not in device_name and 'вход' not in device_name:
                    return i
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                device_name = device['name'].lower()
        
        return None

    def audio_callback(self, indata, frames, time_info, status):
        self.callback_count += 1

        if self.volume_callback or self.frequency_callback:
            if indata is None or len(indata) == 0:
                return
                
            audio_data = indata[:, 0]
            
            volume = np.sqrt(np.mean(audio_data**2))
            self.volume_history.append(volume)
            smoothed_volume = np.mean(list(self.volume_history))
            self.last_volume = smoothed_volume
            
            if self.volume_callback:
                self.volume_callback(smoothed_volume)
            
            if self.frequency_callback and len(audio_data) > 10:
                try:
                    window = np.hanning(len(audio_data))
                    windowed_data = audio_data * window
                    
                    fft_data = np.fft.rfft(windowed_data)
                    frequencies = np.fft.rfftfreq(len(windowed_data), 1/self.sample_rate)
                    magnitude = np.abs(fft_data)
                    
                    low_mask = (frequencies >= 20) & (frequencies < 200)
                    mid_mask = (frequencies >= 200) & (frequencies < 1500)
                    high_mask = (frequencies >= 1500) & (frequencies < 6000)
                    
                    low_freq = np.mean(magnitude[low_mask]) if np.any(low_mask) else 0.001
                    mid_freq = np.mean(magnitude[mid_mask]) if np.any(mid_mask) else 0.001
                    high_freq = np.mean(magnitude[high_mask]) if np.any(high_mask) else 0.001
                    
                    low_freq *= 3
                    
                    self.frequency_history.append((low_freq, mid_freq, high_freq))
                    smoothed_freq = np.mean(list(self.frequency_history), axis=0)
                    self.last_frequencies = smoothed_freq
                    
                    self.frequency_callback(*smoothed_freq)
                        
                except Exception as e:
                    print(f"Error in FFT: {e}")

    def start_capture(self):
        if self.is_running:
            return True

        self.list_audio_devices()
        
        device_index = self.find_loopback_device()
        
        if device_index is None:
            return False

        try:
            self.stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self.audio_callback
            )
            self.is_running = True
            self.stream.start()
            return True
                
        except Exception as e:
            print(f"❌ Failed to start SYSTEM audio capture: {e}")
            return False

    def stop_capture(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_running = False

    def get_debug_info(self):
        return {
            "volume": self.last_volume,
            "frequencies": self.last_frequencies,
            "is_running": self.is_running,
            "callback_count": self.callback_count
        }

    def set_volume_callback(self, callback):
        self.volume_callback = callback

    def set_frequency_callback(self, callback):
        self.frequency_callback = callback

    def close(self):
        self.stop_capture()