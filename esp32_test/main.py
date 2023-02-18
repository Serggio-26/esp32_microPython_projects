from machine import Pin, PWM
import time

pwmLed = PWM(Pin(2))
brightness = 10
pwmLed.duty(brightness)

while True:
    print(f'Brightness = {brightness}')
    pwmLed.duty(brightness)
    time.sleep_ms(50)
    brightness += 50
    if brightness >= 1024:
        brightness = 10
