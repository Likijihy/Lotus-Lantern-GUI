from bleak import BleakClient
from .protocol import (
    turn_on, turn_off,
    set_color, set_brightness,
    set_effect, set_effect_speed,
    EFFECTS
)

CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

async def send_turn_on(client: BleakClient):
    await client.write_gatt_char(CHAR_UUID, turn_on())

async def send_turn_off(client: BleakClient):
    await client.write_gatt_char(CHAR_UUID, turn_off())

async def send_color(client: BleakClient, rgb: tuple[int, int, int]):
    r, g, b = rgb
    await client.write_gatt_char(CHAR_UUID, set_color(r, g, b))

async def send_brightness(client: BleakClient, value: int):
    await client.write_gatt_char(CHAR_UUID, set_brightness(value))

async def send_effect_speed(client: BleakClient, speed: int):
    await client.write_gatt_char(CHAR_UUID, set_effect_speed(speed))

async def send_mode(client: BleakClient, mode: str):
    mode_map = {
        "Статический": "crossfade_white",
        "Переливание": "crossfade_red_green_blue_yellow_cyan_magenta_white",
        "Мерцание": "blink_red_green_blue_yellow_cyan_magenta_white",
        "Радуга": "jump_red_green_blue_yellow_cyan_magenta_white",
        "Стробы": "blink_white",
        "Волна": "crossfade_red_green_blue",
        "Музыкальный": "crossfade_red_green_blue",
    }
    effect_key = mode_map.get(mode)
    if effect_key not in EFFECTS:
        raise ValueError(f"Unknown mode: {mode}")
    effect_code = EFFECTS[effect_key]
    await client.write_gatt_char(CHAR_UUID, set_effect(effect_code))