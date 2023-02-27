# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
# Modified by akleindolph 2022

import time
import board
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_motorkit import MotorKit
import neopixel
import adafruit_veml7700
import adafruit_ahtx0
from adafruit_seesaw.seesaw import Seesaw

pixel_pin = board.A2
num_pixels = 24

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.4, auto_write=False, pixel_order=neopixel.GRBW)
i2c = board.I2C()  # uses board.SCL and board.SDA
kit = MotorKit(i2c=board.I2C())
veml7700 = adafruit_veml7700.VEML7700(i2c)
ahtx0 = adafruit_ahtx0.AHTx0(i2c)
ss = Seesaw(i2c, addr=0x36)
interval = 30
color = "#1700ff"
override = 0 

kit.motor1.throttle = 0  #turn motor off

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

### Feeds ###

# Setup feeds
light_feed = secrets["aio_username"] + "/feeds/arugula.internet-light"
pump_feed = secrets["aio_username"] + "/feeds/arugula.internet-motor"
humidity = secrets["aio_username"] + "/feeds/arugula.humidity"
light = secrets["aio_username"] + "/feeds/arugula.light"
temp = secrets["aio_username"] + "/feeds/arugula.temperature"
moisture = secrets["aio_username"] + "/feeds/arugula.moisture"
manual = secrets["aio_username"] + "/feeds/arugula.manual"
switch = secrets["aio_username"] + "/feeds/arugula.light-switch"

### Code ###

def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO!")
    '''print("Connected to Adafruit IO! Listening for topic changes on %s" % light_feed)
    print("Connected to Adafruit IO! Listening for topic changes on %s" % pump_feed)
    print("Connected to Adafruit IO! Listening for topic changes on %s" % manual)
    print("Connected to Adafruit IO! Listening for topic changes on %s" % switch)'''
    # Subscribe to all changes on the pump_feed.
    client.subscribe(light_feed)
    client.subscribe(pump_feed)
    client.subscribe(manual)
    client.subscribe(switch)
    mqtt_client.publish(pump_feed, 0)
    mqtt_client.publish(manual, 0)
    mqtt_client.publish(switch, 0)


def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from Adafruit IO!")


def message(client, topic, message):
    global override
    # This method is called when a topic the client is subscribed to
    # has a new message.
    
    #print("New message on topic {0}: {1}".format(topic, message))
            
    if(topic == switch):
        if int(message) == 1:
            print("Light is now on")
            pixels.fill(hex_to_rgb("#1700ff"))
            pixels.show()
        else:
            print("Light is now off")
            pixels.fill((0, 0, 0))
            pixels.show()
    
    if(topic == manual):
        if int(message) == 1:
            print("MANUAL OVERRIDE INITIATED")
            override = 1
        else:
            print("Manual Override Deactivated")
            override = 0

            
    if(topic == pump_feed):
        if(override == 1):
            if int(message) == 1:
                print("motor is now on")
                kit.motor1.throttle = int(message)
            else:
                print("motor is now off")
                kit.motor1.throttle = int(message)
        
    if (topic == light_feed):
        if(override == 1):
            print('color is now ' + str(message))
            pixels.fill(hex_to_rgb(str(message)))
            pixels.show()

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
mqtt_client.connect()

def hex_to_rgb(hex):
    hex = hex.lstrip("#")
    rgb = []
    for i in (0, 2, 4):
        decimal = int(hex[i:i+2], 16)
        rgb.append(decimal)
    return tuple(rgb)
    
def water():
    moisture_lvl = ss.moisture_read()
    #500 -> 750
    if(moisture_lvl <= 500):
        kit.motor1.throttle = 1
        
    if(moisture_lvl >= 750):
        kit.motor1.throttle = 0
    
    pass
    
def auto_light():
    light_lvl = veml7700.light
    


while True:
    for i in range(interval):
        try:
            mqtt_client.loop()
            water()
        except:
            pass
        time.sleep(1)
        if (i != 0) and (i < interval):
            if(i % 10 == 0):
                print("time till data dump: " + str(interval - i))
            pass
        else:
            print("sending light data: ", veml7700.light)
            mqtt_client.publish(light, veml7700.light)
        
            print("sending temp data: ", ahtx0.temperature)
            mqtt_client.publish(temp, ahtx0.temperature)
        
            print("sending moisture data: ", ss.moisture_read())
            mqtt_client.publish(moisture, ss.moisture_read())
        
            print("sending humidity data: ", ahtx0.relative_humidity)
            mqtt_client.publish(humidity, ahtx0.relative_humidity)
