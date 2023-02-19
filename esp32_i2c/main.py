from machine import Pin, I2C
from ssd1306 import SSD1306
import machine
import random
import time

machine.freq(240000000)
i2c = I2C(0)
i2c = I2C(1, scl=Pin(18), sda=Pin(19), freq=400000)

print("\n===== I2C =====\n")

devices = i2c.scan()
print(devices)


display = SSD1306(i2c, devices[0])
if not display.fontSet("/fonts/font_7x12.json"):
    print("Couldn't set font")

count = 0

display.clear()
display.fillRectangle(0, 0, SSD1306.LCD_WIDTH - 1, SSD1306.LCD_HEIGHT - 1, SSD1306.OPERATION_XOR)
display.putString('Hello from ESP!', 5, 20, SSD1306.OPERATION_XOR)
time.sleep(5)
display.clear()
while True:

    # y0 = random.randint(0, SSD1306.LCD_HEIGHT)
    # y1 = random.randint(0, SSD1306.LCD_HEIGHT)
    # x0 = random.randint(0, SSD1306.LCD_WIDTH)
    # x1 = random.randint(0, SSD1306.LCD_WIDTH)

    # r_max = int(min(abs(x0-x1), abs(y0-y1))/2)
    # r = random.randint(0, r_max)

    # display.drawRoundRectangle(x0, y0, x1, y1, r, SSD1306.OPERATION_XOR)

    y0 = random.randint(0, SSD1306.LCD_HEIGHT)
    x0 = random.randint(0, SSD1306.LCD_WIDTH)

    r_max = int(min(abs(x0-SSD1306.LCD_WIDTH-1), abs(y0-SSD1306.LCD_HEIGHT-1), x0, y0))
    r = random.randint(0, r_max)

    display.drawCircle(x0, y0, r, SSD1306.OPERATION_OR)
    
    time.sleep_ms(100)
    count += 1

    if count == 100:
        display.clear()
        count = 0

