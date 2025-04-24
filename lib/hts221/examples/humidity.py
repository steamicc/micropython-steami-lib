from machine import I2C
from hts221 import HTS221
from time import sleep_ms
import pyb

i2c = I2C(1)

sleep_ms(1000)

sensor = HTS221(i2c)

led_red = pyb.LED(1)
led_green = pyb.LED(2)
led_blue = pyb.LED(3)


def red() -> None:
    led_red.on()
    led_green.off()
    led_blue.off()


def green() -> None:
    led_red.off()
    led_green.on()
    led_blue.off()


def blue() -> None:
    led_red.off()
    led_green.off()
    led_blue.on()


while True:
    sleep_ms(1000)

    temp = sensor.temperature()
    humi = sensor.humidity()

    print("Temperature : % .1f °C, Humidity : % .1f %% " % (temp, humi), end="")

    if temp > 25:
        red()
        print("🥵")
    elif temp > 16 and temp <= 25:
        green()
        print("😃")
    else:
        blue()
        print("🥶")
