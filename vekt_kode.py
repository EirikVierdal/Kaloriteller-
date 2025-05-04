# vekt_med_knapper_og_send.py

from machine import Pin
from hx711 import HX711
import network
import urequests
import time

# ──────────────────────────────
# 1) HX711-oppsett
# ──────────────────────────────
hx = HX711(d_out=5, pd_sck=4)

# Dine siste kalibreringsverdier
offset = 5858
calibration_factor = 430.7473

# ──────────────────────────────
# 2) Knapper (med Pull-Up)
# ──────────────────────────────
btn_tare  = Pin(14, Pin.IN, Pin.PULL_UP)  # nullstill
btn_send  = Pin(15, Pin.IN, Pin.PULL_UP)  # send

last_tare = 0
last_send = 0
DEBOUNCE  = 200  # ms

# ──────────────────────────────
# 3) Wi-Fi-innstillinger (kun Pico W)
# ──────────────────────────────
SSID    = '********'
PASSWORD= '********'
API_URL = 'https://g3hmzvj1-3000.euw.devtunnels.ms/'  # endre til ditt endepunkt

def connect_wifi(timeout_ms=10000):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        wlan.active(True)
        wlan.connect(SSID, PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                print("Wi-Fi: timeout")
                return False
            time.sleep(0.1)
    print("Wi-Fi tilkoblet", wlan.ifconfig())
    return True

# ──────────────────────────────
# 4) Funksjoner
# ──────────────────────────────
def do_tare():
    """Nullstiller vekta (offset) ved å ta 20 råmålinger."""
    global offset
    print("TARE: måler 20 råverdier…")
    total = 0
    for _ in range(20):
        total += hx.read()
        time.sleep(0.05)
    offset = total // 20
    print("Ny offset =", offset)

def send_weight(w):
    """Sender vekten som JSON via HTTP POST."""
    data = {'weight': w}
    try:
        if not connect_wifi():
            return
        resp = urequests.post(API_URL, json=data)
        print("HTTP", resp.status_code, resp.text)
        resp.close()
    except Exception as e:
        print("Send Error:", e)

# ──────────────────────────────
# 5) Hovedløkken
# ──────────────────────────────
print("Starter. Knapp14=Tare, Knapp15=Send")
while True:
    # a) Les og konverter til gram
    raw = hx.read() - offset
    w = raw / calibration_factor
    weight = round(w)

    # b) Tare-knapp
    if not btn_tare.value():
        now = time.ticks_ms()
        if time.ticks_diff(now, last_tare) > DEBOUNCE:
            do_tare()
            last_tare = now

    # c) Send-knapp
    if not btn_send.value():
        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) > DEBOUNCE:
            print("Sender vekt:", weight, "g")
            send_weight(weight)
            last_send = now

    # d) Utskrift til konsoll
    print(f"Vekt: {weight} g")
    time.sleep(2)
