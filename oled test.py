from machine import Pin, SPI
from ssd1306 import SSD1306_SPI

# SPI-oppsett
spi = SPI(0, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19))
dc = Pin(17, Pin.OUT)
res = Pin(16, Pin.OUT)
cs = Pin(20, Pin.OUT)

# OLED-oppsett
oled = SSD1306_SPI(128, 64, spi, dc, res, cs)

# Rens skjermen
oled.fill(0)
oled.show()

# Skriv tekst
oled.text("Test OLED", 0, 0)
oled.text("Funker det?", 0, 10)
oled.show()
